# -*- coding: utf-8 -*-
"""
Created on Thu Jul  6 11:38:34 2023
"""
import pandas as pd
import io
from requests_cache import CachedSession
from requests import Session
from datetime import timedelta
import logging
import numpy as np
import time
from tqdm import tqdm
from pebble import ThreadPool
from pynsee.localdata import get_area_list
from rapidfuzz import fuzz, process
from unidecode import unidecode

from french_cities.utils import init_pynsee, patch_the_patch


logger = logging.getLogger(__name__)


def _process_departements_from_postal(
    df: pd.DataFrame, source: str, alias: str, session: Session = None
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

    Returns
    -------
    df : pd.DataFrame
        Updated DataFrame with departement's codes

    """

    if not session:
        session = CachedSession(
            allowable_methods=("GET", "POST"),
            expire_after=timedelta(days=30),
        )

    postal_codes = df[[source]].drop_duplicates(keep="first")
    files = [
        (
            "data",
            (
                "data.csv",
                postal_codes.to_csv(index=False, encoding="utf8"),
                "text/csv; charset=utf-8",
            ),
        ),
        ("postcode", (None, source)),
        ("result_columns", (None, source)),
        ("result_columns", (None, "result_context")),
    ]

    with patch_the_patch():
        r = session.post(
            # recherche grâce à l'API de la BAN
            "https://api-adresse.data.gouv.fr/search/csv/",
            files=files,
        )

    if not r.ok:
        raise Exception(
            f"Failed to query BAN's API with {files=} - response was {r}"
        )
    result = pd.read_csv(io.BytesIO(r.content), dtype=str)
    result[alias] = (
        result["result_context"].str.split(",", expand=True)[0].str.strip(" ")
    )
    result = result.drop("result_context", axis=1)

    # where code is unknown, use Christian Quest Dataset with Cedex codes and
    # OpenDataSoft API (v2.1 contrairement à la doc disponible) en Freemium
    # https://www.data.gouv.fr/fr/datasets/liste-des-cedex/#_
    # https://public.opendatasoft.com/explore/dataset/correspondance-code-cedex-code-insee/information/?flg=fr&q=code%3D68013&lang=fr
    def get(x):
        while True:
            r = session.get(
                # recherche "en masse" grâce à l'API de la BAN
                "https://public.opendatasoft.com/api/explore/v2.1/catalog/datasets/correspondance-code-cedex-code-insee/records",
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
            elif r.status_code == 429:
                time.sleep(1)
            else:
                logger.warning(
                    f"Error occured on code {x} on OpenDataSoft's API"
                )
                return None
        results = r.json()["results"]

        for dict_ in results:
            dict_.update({source: x})
        return results

    ix = result[result[alias].isnull()].index
    if len(ix) > 0:
        logger.info("postal codes unrecognized - maybe Cedex codes")
        args = result.loc[ix, source].dropna().tolist()
        results_cedex = []
        with tqdm(
            total=len(args), desc="Querying OpenDataSoft API", leave=False
        ) as pbar:
            with ThreadPool(10) as pool:
                future = pool.map(get, args)
                results_iterator = future.result()
                while True:
                    try:
                        this_result = next(results_iterator)
                        if this_result:
                            results_cedex += this_result
                    except StopIteration:
                        break
                    finally:
                        pbar.update(1)
        results_cedex = pd.DataFrame(results_cedex)

        # Select main city in case of discordant results. For instance, with
        # postcode=74105, you'll get:
        #    insee       nom_dep          libelle          nom_com
        # 0  74145  HAUTE-SAVOIE  ANNEMASSE CEDEX          Juvigny
        # 1  74012  HAUTE-SAVOIE  ANNEMASSE CEDEX        Annemasse
        # 2  74305  HAUTE-SAVOIE  ANNEMASSE CEDEX   Ville-la-Grand
        # 3  74298  HAUTE-SAVOIE  ANNEMASSE CEDEX  Vétraz-Monthoux

        if not results_cedex.empty:
            for f in ["libelle", "nom_com"]:
                results_cedex[f] = (
                    results_cedex[f]
                    .fillna("")
                    .str.upper()
                    .apply(unidecode)
                    .str.split(r"\W+")
                    .str.join(" ")
                    .str.strip(" ")
                    .replace("", np.nan)
                )
            results_cedex["libelle"] = results_cedex["libelle"].str.replace(
                r" CEDEX", ""
            )
            results_cedex["score"] = results_cedex[
                ["libelle", "nom_com"]
            ].apply(lambda xy: fuzz.token_set_ratio(*xy), axis=1)

            results_cedex = results_cedex.sort_values([source, "score"])
            results_cedex = results_cedex.drop_duplicates(source, keep="last")
            results_cedex = results_cedex.drop(
                ["nom_com", "score", "libelle"], axis=1
            )
            results_cedex = results_cedex.drop_duplicates()

            results_cedex = _process_departements_from_insee_code(
                results_cedex,
                source="insee",
                alias="dep_cedex",
                session=session,
            )
            result = result.merge(results_cedex, on=source, how="left")
            result.loc[ix, alias] = result.loc[ix, "dep_cedex"]
            result = result.drop(
                list(
                    set(results_cedex.columns)
                    - {
                        source,
                    }
                ),
                axis=1,
            )

    ix = result[result[alias].isnull()].index
    if len(ix) > 0:
        # Still no results -> assume we can use the first characters of
        # postcode anyway
        result.loc[ix, alias] = _process_departements_from_insee_code(
            result.loc[ix],
            source=source,
            alias="dep",
            session=session,
        )["dep"]

    logger.info("résultat obtenu")

    df = df.merge(result, on=source, how="left")

    return df


def _process_departements_from_insee_code(
    df: pd.DataFrame, source: str, alias: str, session: Session = None
) -> pd.DataFrame:
    """
    Compute departement's codes from official french cities codes (COG INSEE).
    Adds the result as a new column to dataframe under the label 'alias'.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing official cities codes
    source : str
        Field containing the official codes (INSEE COG)
    alias : str
        Column to store the departements' codes unto
    session : Session, optional
        Web session. The default is None (and will use a CachedSession with
        30 days expiration)
        **ignored argument, set only for coherence with
        _process_departements_from_postal**

    Returns
    -------
    df : pd.DataFrame
        Updated DataFrame with departement's codes

    """
    df[alias] = df[source].str[:2]

    ix = df[df[alias] == "97"].index
    df.loc[ix, alias] = df.loc[ix, source].str[:3]

    return df


def find_departements(
    df: pd.DataFrame,
    source: str,
    alias: str,
    type_code: str,
    session: Session = None,
) -> pd.DataFrame:
    """
    Compute departement's codes from postal or official codes (ie. INSEE COG)'
    Adds the result as a new column to dataframe under the label 'alias'.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing official cities codes
    source : str
        Field containing the post or official codes
    alias : str
        Column to store the departements' codes unto
    type_code : str
        Type of codes passed under `alias` label. Should be either 'insee' for
        official codes or 'postcode' for postal codes.
    session : Session, optional
        Web session. The default is None (and will use a CachedSession with
        30 days expiration)

    Raises
    ------
    ValueError
        If type_code not among "postcode", "insee".

    Returns
    -------
    df : pd.DataFrame
        Updated DataFrame with departement's codes

    """
    if type_code not in {"postcode", "insee"}:
        msg = (
            "type_code must be among ('postcode', 'insee') - "
            f"found {type_code} instead"
        )
        raise ValueError(msg)

    init_pynsee()

    df = df.copy()
    if type_code == "postcode":
        func = _process_departements_from_postal
    elif type_code == "insee":
        func = _process_departements_from_insee_code
    return func(df, source, alias, session)


def find_departements_from_names(
    df: pd.DataFrame, label: str, alias: str = "DEP_CODE"
) -> pd.DataFrame:
    """
    Retrieve departement's codes from their names.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing official departement's names
    label : str
        Field containing the label of the departements
    alias : str, optional
        Column to store the departements' codes unto.
        Default is "DEP_CODE"

    Returns
    -------
    df : pd.DataFrame
        Updated DataFrame with departement's codes

    """

    init_pynsee()
    candidates = get_area_list("departements")
    candidates = candidates[["CODE", "TITLE"]]
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
        df[label]
        .apply(unidecode)
        .str.upper()
        .str.replace(r"\W+", " ", regex=True)
    )

    df[alias] = df["FORMATTED"].apply(
        lambda x: candidates[
            process.extractOne(
                x,
                candidates_keys,
                scorer=fuzz.ratio,
                score_cutoff=80,
            )[0]
        ]
    )
    df = df.drop("FORMATTED", axis=1)

    return df
