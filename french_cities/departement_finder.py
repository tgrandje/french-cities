# -*- coding: utf-8 -*-
"""
Created on Thu Jul  6 11:38:34 2023

Module used to recognize departments, either from names, cities' official codes
or cities' postcodes.
"""

from datetime import timedelta, date
import io
import logging
import os
import time

import diskcache
import pandas as pd
from pebble import ThreadPool
from rapidfuzz import fuzz, process
from requests_cache import CachedSession
from requests import Session
from tqdm import tqdm
from unidecode import unidecode

from french_cities import DIR_CACHE
from french_cities.constants import THREADS
from french_cities.utils import init_pynsee, silence_sirene_logs
from french_cities.ultramarine_pseudo_cog import (
    get_departements_and_ultramarines,
)
from french_cities.vintage import set_vintage


logger = logging.getLogger(__name__)


def _process_departements_from_postal(
    df: pd.DataFrame,
    source: str,
    alias: str,
    session: Session = None,
    authorize_duplicates: bool = False,
    threads: int = THREADS,
    **kwargs,
) -> pd.DataFrame:
    """
    Retrieve departement's code from postoffice code. Adds the result as a new
    column to dataframe under the label 'alias'. Uses the BAN (Base Adresse
    Nationale under the hood) and OpenDataSoft's freemium API in backoffice (
    mostly in case of "Cedex" codes)

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing postal codes
    source : str
        Field containing the postal codes
    alias : str
        Column to store the departements' codes unto
    session : Session, optional
        Web session. The default is None (and will use a CachedSession with
        30 days expiration)
    authorize_duplicates : bool, optional
        If True, authorize duplication of results when multiple results are
        acceptable for a given postcode (for instance, 13780 can result to
        either 13 or 83). If False, duplicates will be removed, hence no
        result will be available. False by default.
    threads : int, optional
        Number of threads to use. Default is 10.
    kwargs : ignored
        **ignored argument, set only for coherence with other functions**

    Returns
    -------
    df : pd.DataFrame
        Updated DataFrame with departement's codes

    """

    cache_departments = diskcache.Cache(os.path.join(DIR_CACHE, "deps"))

    if not session:
        session = CachedSession(
            cache_name=os.path.join(DIR_CACHE, "find-department"),
            allowable_methods=("GET", "POST"),
            expire_after=timedelta(days=30),
        )
        proxies = {}
        proxies["http"] = os.environ.get("http_proxy", None)
        proxies["https"] = os.environ.get("https_proxy", None)
        session.proxies.update(proxies)

    df["#CachedResult#"] = df[source].apply(cache_departments.get)

    # Download official postcodes dataset from API
    # https://datanova.laposte.fr/datasets/laposte-hexasmal
    url = (
        "https://datanova.laposte.fr/data-fair/api/v1/datasets/"
        "laposte-hexasmal/raw"
    )

    r = session.get(url)
    base = pd.read_csv(
        io.BytesIO(r.content), sep=";", encoding="cp1252", dtype=str
    )
    base = base[["#Code_commune_INSEE", "Code_postal"]]
    base = _process_departements_from_insee_code(
        base,
        "#Code_commune_INSEE",
        alias,
        do_set_vintage=False,
        threads=threads,
    )
    base = base[["Code_postal", alias]].rename({"Code_postal": source}, axis=1)
    base = base.drop_duplicates(keep="first")

    ix = df[df["#CachedResult#"].isnull()].index

    result_hexasmal = df.loc[ix].merge(base, on=source, how="inner")
    result_hexasmal = (
        result_hexasmal[[alias, source]].dropna().drop_duplicates()
    )

    ix = df[df["#CachedResult#"].isnull()].index
    postal_codes_ban = (
        df.loc[ix, [source]]
        .merge(
            result_hexasmal[[source]], on=source, how="left", indicator=True
        )
        .query('_merge=="left_only"')
        .drop("_merge", axis=1)
        .drop_duplicates(keep="first")
    )
    if not postal_codes_ban.empty:

        files = [
            (
                "data",
                (
                    "data.csv",
                    postal_codes_ban.to_csv(index=False, encoding="utf8"),
                    "text/csv; charset=utf-8",
                ),
            ),
            ("postcode", (None, source)),
            ("result_columns", (None, source)),
            ("result_columns", (None, "result_context")),
        ]

        r = session.post(
            # recherche grâce à l'API de la BAN
            "https://api-adresse.data.gouv.fr/search/csv/",
            files=files,
        )

        if not r.ok:
            raise ValueError(
                f"Failed to query BAN's API with {files=} - response was {r}"
            )
        result = pd.read_csv(io.BytesIO(r.content), dtype=str)
        result[alias] = (
            result["result_context"]
            .str.split(",", expand=True)[0]
            .str.strip(" ")
        )
        result = result.drop("result_context", axis=1)
        result_ban = result[result[alias].notnull()].drop_duplicates()
    else:
        result_ban = pd.DataFrame()

    result = pd.concat([result_hexasmal, result_ban]).drop_duplicates()

    ix = df[df["#CachedResult#"].isnull()].index
    postal_codes_cedex = (
        df.loc[ix, [source]]
        .merge(result[[source]], on=source, how="left", indicator=True)
        .query('_merge=="left_only"')
        .drop("_merge", axis=1)
        .drop_duplicates(keep="first")
    )

    # where code is unknown, use Christian Quest Dataset with Cedex codes and
    # OpenDataSoft API (v2.1 contrairement à la doc disponible) en Freemium
    # https://www.data.gouv.fr/fr/datasets/liste-des-cedex/#_
    # https://public.opendatasoft.com/explore/dataset/correspondance-code-cedex-code-insee/information/?flg=fr&q=code%3D68013&lang=fr
    def get(x):
        while True:
            r = session.get(
                # recherche "en masse" grâce à l'API de la BAN
                "https://public.opendatasoft.com/api/explore/v2.1/catalog/"
                "datasets/correspondance-code-cedex-code-insee/records",
                params={
                    "select": "insee,libelle,nom_com",
                    "where": f"code={x}",
                    "limit": "10",
                    "offset": "0",
                    "timezone": "UTC",
                    "include_links": "false",
                    "include_app_metas": "false",
                },
            )
            if r.ok:
                break
            if r.status_code == 429:
                time.sleep(1)
            else:
                logger.warning(
                    "Error occured on code %s on OpenDataSoft's API", x
                )
                return None
        results = r.json()["results"]

        for dict_ in results:
            dict_.update({source: x})
        return results

    if not postal_codes_cedex.empty:
        logger.info("postal codes unrecognized - maybe Cedex codes")
        args = postal_codes_cedex[source].dropna().tolist()
        result_cedex = []
        with tqdm(
            total=len(args), desc="Querying OpenDataSoft API", leave=False
        ) as pbar:
            with ThreadPool(threads) as pool:
                future = pool.map(get, args)
                results_iterator = future.result()
                while True:
                    try:
                        this_result = next(results_iterator)
                        if this_result:
                            result_cedex += this_result
                    except StopIteration:
                        break
                    finally:
                        pbar.update(1)
        result_cedex = pd.DataFrame(result_cedex).drop_duplicates()

        if not result_cedex.empty:
            # Keep only results with valid department
            result_cedex = _process_departements_from_insee_code(
                result_cedex,
                source="insee",
                alias=alias,
                session=session,
                threads=threads,
            )
            ix = result_cedex[result_cedex[alias].notnull()].index
            result_cedex = result_cedex.loc[
                ix, [source, alias]
            ].drop_duplicates(keep="first")
    else:
        result_cedex = pd.DataFrame()

    result = pd.concat(
        [result_hexasmal, result_ban, result_cedex]
    ).drop_duplicates()

    ix = df[df["#CachedResult#"].isnull()].index
    postal_codes_missing = (
        df.loc[ix, [source]]
        .merge(result[[source]], on=source, how="left", indicator=True)
        .query('_merge=="left_only"')
        .drop("_merge", axis=1)
        .drop_duplicates(keep="first")
    )

    if not postal_codes_missing.empty:
        # Still no results -> assume we can use the first characters of
        # postcode anyway (and set do_set_vintage to False, as this may be
        # entirely wrong codes, but the first digits may at least be ok)
        last_resort_results = _process_departements_from_insee_code(
            postal_codes_missing,
            source=source,
            alias=alias,
            session=session,
            do_set_vintage=False,
            threads=threads,
        )
        last_resort_results = last_resort_results.dropna()
    else:
        last_resort_results = pd.DataFrame()

    result = pd.concat(
        [result_hexasmal, result_ban, result_cedex, last_resort_results]
    )

    result = result.drop_duplicates()
    if not authorize_duplicates:
        result = result.drop_duplicates(source, keep=False)

    logger.info("résultat obtenu")

    df = df.merge(result, on=source, how="left").drop_duplicates()
    ix = df[df["#CachedResult#"].notnull()].index
    df.loc[ix, alias] = df.loc[ix, "#CachedResult#"]
    ix = df[df["#CachedResult#"].isnull()].index

    new_cache_values = df.loc[ix, [source, alias]].drop_duplicates()

    # Cache only non-duplicated results!
    new_cache_values = new_cache_values.drop_duplicates(source, keep=False)

    new_cache_values = dict(new_cache_values.values)
    for key, val in new_cache_values.items():
        cache_departments[key] = val

    df = df.drop("#CachedResult#", axis=1)

    cache_departments.close()
    return df


def _process_departements_from_insee_code(
    df: pd.DataFrame,
    source: str,
    alias: str,
    do_set_vintage: bool = True,
    threads: int = True,
    **kwargs,
) -> pd.DataFrame:
    """
    Compute departement's codes from official french cities codes (COG INSEE).
    Adds the result as a new column to dataframe under the label 'alias'.

    Note that only valid codes will be kept, but that the computation will be
    performed with the first characters of the city code, for performance's
    sake (after trying to set the dataset's vintage to the current year)

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing official cities codes
    source : str
        Field containing the official codes (INSEE COG)
    alias : str
        Column to store the departements' codes unto
    do_set_vintage : bool, optional
        If True, set a vintage projection for df. If False, don't bother (will
        be faster). Should be False when df was already computed from a given
        function out of pynsee or french-cities. Should be True when used on
        almost any other dataset.
        The default is True.
    threads : int, optional
        Number of threads to use. Default is 10.
    kwargs : ignored
        **ignored arguments, set only for coherence with other function**

    Returns
    -------
    df : pd.DataFrame
        Updated DataFrame with departement's codes

    """
    init_pynsee()
    deps = get_departements_and_ultramarines(date="*").rename(
        {"CODE": "#DEP_CODE#"}, axis=1
    )
    deps = deps[["#DEP_CODE#"]].drop_duplicates(keep="first")

    if do_set_vintage:
        # Project into last vintage (to prevent mistakes for cities having
        # change of department)
        df["#CODE_INIT#"] = df[source].copy()
        df = set_vintage(df, date.today().year, source, threads=threads)

    df[alias] = df[source].str[:2]

    ix = df[df[alias] == "97"].index
    df.loc[ix, alias] = df.loc[ix, source].str[:3]

    # Remove unvalid results (ultramarine collectivity, monaco, ...)
    df = df.merge(deps, left_on=alias, right_on="#DEP_CODE#", how="left")
    df = df.drop(alias, axis=1).rename({"#DEP_CODE#": alias}, axis=1)

    if do_set_vintage:
        df = df.drop(source, axis=1)
        df = df.rename({"#CODE_INIT#": source}, axis=1)

    return df


def _find_departements_from_names(
    df: pd.DataFrame,
    source: str,
    alias: str,
    **kwargs,
) -> pd.DataFrame:
    """
    Retrieve departement's codes from their names.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing official departement's names
    source : str
        Field containing the label of the departements
    alias : str, optional
        Column to store the departements' codes unto.
        Default is "DEP_CODE"
    kwargs : ignored
        **ignored argument, set only for coherence with other functions**

    Returns
    -------
    df : pd.DataFrame
        Updated DataFrame with departement's codes

    """

    init_pynsee()
    candidates = get_departements_and_ultramarines("*")
    candidates = candidates[["CODE", "TITLE"]].drop_duplicates()
    candidates["TITLE"] = (
        candidates["TITLE"]
        .apply(unidecode)
        .str.upper()
        .str.replace(r"\W+", " ", regex=True)
    )
    candidates = dict(candidates[["TITLE", "CODE"]].values)
    candidates_keys = list(candidates.keys())

    df = df.copy()
    df["FORMATTED"] = (
        df[source]
        .apply(unidecode)
        .str.upper()
        .str.replace(r"\W+", " ", regex=True)
    )

    def try_extract_one(x):
        results = process.extractOne(
            x,
            candidates_keys,
            scorer=fuzz.ratio,
            score_cutoff=80,
        )
        try:
            return candidates[results[0]]
        except (TypeError, KeyError):
            return None

    df[alias] = df["FORMATTED"].apply(try_extract_one)
    df = df.drop("FORMATTED", axis=1)

    return df


@silence_sirene_logs
def find_departements(
    df: pd.DataFrame,
    source: str,
    alias: str,
    type_field: str,
    session: Session = None,
    authorize_duplicates: bool = False,
    do_set_vintage: bool = True,
    threads: int = THREADS,
) -> pd.DataFrame:
    """
    Compute departement's codes from postal, official codes (ie. INSEE COG)
    or labels in full text.
    Adds the result as a new column to dataframe under the label 'alias'.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing official cities codes
    source : str
        Field containing the post codes, official codes or labels
    alias : str
        Column to store the departements' codes unto
    type_field : str
        Type of codes passed under `alias` label. Should be either 'insee' for
        official codes, 'postcode' for postal codes or 'label' for labels.
    session : Session, optional
        Web session. The default is None (and will use a CachedSession with
        30 days expiration)
    authorize_duplicates : bool, optional
        If True, authorize duplication of results when multiple results are
        acceptable for a given postcode (for instance, 13780 can result to
        either 13 or 83 ). If False, duplicates will be removed, hence no
        result will be available. False by default.
    do_set_vintage : bool, optional
        If True, set a vintage projection for df. If False, don't bother (will
        be faster). Should be False when df was already computed from a given
        function out of pynsee or french-cities. Should be True when used on
        almost any other dataset.
        The default is True.
    threads : int, optional
        Number of threads to use. Default is 10.

    Raises
    ------
    ValueError
        If type_field not among "postcode", "insee", "labels".

    Returns
    -------
    df : pd.DataFrame
        Updated DataFrame with departement's codes

    """

    if type_field not in {"postcode", "insee", "label"}:
        msg = (
            "type_field must be among ('postcode', 'insee', 'label') - "
            f"found {type_field=} instead"
        )
        raise ValueError(msg)

    init_pynsee()

    df = df.copy()
    if type_field == "postcode":
        func = _process_departements_from_postal
    elif type_field == "insee":
        func = _process_departements_from_insee_code
    else:
        func = _find_departements_from_names
    return func(
        df=df,
        source=source,
        alias=alias,
        session=session,
        authorize_duplicates=authorize_duplicates,
        do_set_vintage=do_set_vintage,
        threads=threads,
    )
