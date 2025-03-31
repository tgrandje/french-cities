# -*- coding: utf-8 -*-
"""
Created on Thu Jul  6 11:38:34 2023

Module used to recognize cities.

"""
from datetime import date, timedelta
from functools import lru_cache
import hashlib
import io
import logging
import os
import socket
import time
from typing import Union
import warnings

import diskcache
import geopandas as gpd
import numpy as np
import pandas as pd
from pebble import ThreadPool
from pynsee.geodata import get_geodata
from pyproj import Transformer
from requests_cache import CachedSession
from requests import Session
from rapidfuzz import fuzz
from rapidfuzz.process import cdist
from tqdm import tqdm
from unidecode import unidecode

try:
    # Optional dependencies
    from geopy.extra.rate_limiter import RateLimiter
    from geopy.geocoders import Nominatim
except ModuleNotFoundError:
    pass

from french_cities import DIR_CACHE
from french_cities.constants import THREADS
from french_cities.vintage import set_vintage
from french_cities.departement_finder import find_departements
from french_cities.utils import init_pynsee, silence_sirene_logs
from french_cities.ultramarine_pseudo_cog import get_cities_and_ultramarines


logger = logging.getLogger(__name__)


def get_machine_user_agent() -> str:
    """
    Get a fixed User Agent for a given machine. Used to fullfill Nominatim's
    usage policy.

    Returns
    -------
    str
        User-Agent string
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]

    m = hashlib.sha256()
    m.update(bytes(ip, encoding="utf8"))
    digest = m.hexdigest()

    return f"french-cities-{digest}"


def _cleanup_results(
    df: pd.DataFrame, alias_postcode: str, threads: int = THREADS
) -> pd.DataFrame:
    """
    Quick and dirty function to remove multiple candidates for cities
    recognition.

    This function process cases where multiple candidates are found, mostly
    because there may be multiple departments candidates found through
    postcode.
    Perfect homonyms between two departments are eliminated.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with candidates, expected columns are alias_postcode,
        'city_cleaned', 'dep', 'CODE'
    alias_postcode : str
        Field used to store the postcode
    threads : int, optional
        Number of threads to use. Default is 10.

    Returns
    -------
    df : pd.DataFrame
        Cleaned DataFrame.

    """

    init_pynsee()

    cities = get_cities_and_ultramarines(date="*", threads=threads)
    cities["TITLE_SHORT"] = (
        cities["TITLE_SHORT"]
        .str.upper()
        .apply(unidecode)
        .str.split(r"\W+")
        .str.join(" ")
        .str.strip(" ")
    )
    cities = cities.loc[:, ["TITLE_SHORT", "CODE"]]

    df = df.drop_duplicates(keep="first")

    # Find duplicates (should be induced by multiple candidates for
    # departments computed from postcodes)

    keys = [alias_postcode, "city_cleaned"]
    dups = df[df.duplicated(keys, keep=False)]

    # Select where duplicated have been found in at most one department
    ok = dups[dups.CODE.notnull()]
    ok = ok.drop_duplicates(keys, keep=False)

    # And remove their pendant with empty results
    ko = (
        df[df["CODE"].isnull()]
        .reset_index(drop=False)
        .merge(ok[keys], how="inner", on=keys)
    )
    df = df.drop(ko["index"])

    dups = df[df.duplicated(keys, keep=False)]

    # Case where there are exact homonyms cities within each department, drop
    # the results (and hope for better discrimination using the BAN)
    dups = (
        dups.reset_index(drop=False)
        .merge(cities, on="CODE", how="inner")
        .drop_duplicates()
    )
    dups = dups[dups.duplicated(keys + ["TITLE_SHORT"], keep=False)]
    df.loc[dups["index"], "CODE"] = np.nan
    df = df.drop_duplicates()

    # IN any other case, keep the best fuzzy match, whatever the department's
    # origin
    dups = df[df.duplicated(keys, keep=False)]

    dups = (
        dups.reset_index(drop=False)
        .merge(cities, on="CODE", how="inner")
        .drop_duplicates()
    )

    dups["score"] = dups[["city_cleaned", "TITLE_SHORT"]].apply(
        lambda xy: fuzz.token_sort_ratio(*xy), axis=1
    )

    # dups[["city_cleaned", "TITLE_SHORT", "score"]]
    ok = (
        dups[dups.score > 80]
        .fillna("")
        .groupby(keys, as_index=False)[dups.columns.tolist()]
        .apply(lambda df: df[df["score"] == df["score"].max()])
    )
    ko = set(dups["index"]) - set(ok["index"])
    df = df.drop(list(ko))

    return df


@silence_sirene_logs
def find_city(
    df: pd.DataFrame,
    year: str = "last",
    x: Union[str, bool] = "x",
    y: Union[str, bool] = "y",
    dep: Union[str, bool] = "dep",
    city: Union[str, bool] = "city",
    address: Union[str, bool] = "address",
    postcode: Union[str, bool] = "postcode",
    field_output: str = "insee_com",
    epsg: int = None,
    session: Session = None,
    use_nominatim_backend: bool = False,
    threads: int = THREADS,
) -> pd.DataFrame:
    """
    Find cities in a dataframe using multiple methods (either based on
    valid geolocation or lexical fields).

    Do note that the results based on geolocation will be approximative as the
    IGN's WFS data is not vintaged (yet ?). The spatial join will then be
    computed against latest available data. A reprojection in the desired
    vintage will be done afterwards, but cities joined during this lapse time
    will NOT be correctly found.

    Nonetheless, recognition based on lexical fields is also unperfect. These
    will use the Base Adresse Nationale (BAN) API, but results can't be
    guaranteed. The results using geolocation will then be given precedence.

    To activate geolocation recognition, 2 criteria must be satisfied:
        - valids x and y fields (which exact labels will be passed as x and y
          arguments)
        - valid EPSG code related to the current projection

    Lexical recognition will try to use the following fields (in that order
    of precedence):
        - department + city label (fuzzy matching through python)
        - postcode + city label (through the BAN)
        - address + postcode + city label (through the BAN)
        - department + city label (through the BAN)
        - postcode + city label (through Nominatim, if activated)
        - dep + city label (through Nominatim, if activated)

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame onto which city recognition should be perfomed
    year : str, optional
        Desired vintage for cities. year should be of a type castable to int or
        'last'. The default is "last".
    x : str, optional
        Field (column) containing the x coordinates values. Set to False if
        not available. The default is "x".
    y : str, optional
        Field (column) containing the y coordinates values. Set to False if
        not available. The default is "y".
    dep : str, optional
        Field (column) containing the department values. Set to False if
        not available. The default is "dep".
    city : str, optional
        Field (column) containing the city label values. Set to False if
        not available. The default is "city".
    address : str, optional
        Field (column) containing the addresses values. Set to False if
        not available. The default is "address".
    postcode : str, optional
        Field (column) containing the post office codes values. Set to False if
        not available. The default is "postcode".
    field_output : str, optional
        Column to store the cities code into. The default is "insee_com".
    epsg : int, optional
        EPSG code of projection. The default is None.
    session : Session, optional
        Requests Session to use for web queries to APIs. Note that pynsee
        (used under the hood for geolocation recognition) uses it's own
        session. The default is None (and will use a CachedSession with
        30 days expiration)
    use_nominatim_backend : bool, optional
        If set to True, will try to use the Nominatim API in last resort. This
        might slow the process as the API's rate is on one request per second.
        Please read Nominatim Usage Policy at
        https://operations.osmfoundation.org/policies/nominatim/
    threads : int, optional
        Number of threads to use. Default is 10.

    Raises
    ------
    ValueError
        If year is not castable to int or equals to "last", or if no columns
        have been found which will match either (x, y), (postcode, city), or
        (dep, city)

    Returns
    -------
    pd.DataFrame
        Initial dataframe with a new column containing cities' codes (labelled
        according to `field_output` value.)

    """

    index_original_name = df.index.name
    df.index.name = "#INDEX#"
    df = df.reset_index(drop=False)

    init_pynsee()

    if year != "last":
        try:
            int(year)
        except ValueError as exc:
            raise ValueError(
                "year should either be castable to int or 'last', "
                f"found {year} instead"
            ) from exc

    columns = set(df.columns)
    configurations = [
        {postcode, city},
        {dep, city},
    ]
    if epsg:
        configurations.append({x, y})
    elif len({x, y} - columns) == 0:
        logger.warning(
            "x and y columns where found, but a valid EPSG projection was "
            "not set: geolocation will not be performed"
        )
    if not any(len(conf - columns) == 0 for conf in configurations):
        msg = f"All columns among {configurations} are necessary"
        raise ValueError(msg)

    if not session:
        session = CachedSession(
            cache_name=os.path.join(DIR_CACHE, "find-city"),
            allowable_methods=("GET", "POST"),
            expire_after=timedelta(days=30),
        )
        proxies = {}
        proxies["http"] = os.environ.get("http_proxy", None)
        proxies["https"] = os.environ.get("https_proxy", None)
        session.proxies.update(proxies)

    # User geolocation first
    if len({x, y} - columns) == 0 and epsg:
        # On peut travailler à partir de la géoloc
        df = _find_from_geoloc(
            epsg, df, year, x, y, field_output, threads=threads
        ).rename({field_output: "candidat_0"}, axis=1)
    try:
        df["candidat_0"]
    except KeyError:
        df = df.assign(candidat_0=np.nan)

    # Preprocess cities names
    if city in set(df.columns):
        ix = df[(df[city].notnull()) & (df.candidat_0.isnull())].index
        unique = df.loc[ix, [city]].drop_duplicates(keep="first")
        unique["city_cleaned"] = (
            unique[city]
            .str.replace(
                r" \(.*\)$", "", regex=True
            )  # Neuville-Housset (La) -> Neuville-Housset
            .str.upper()
            .apply(unidecode)
            .str.split(r"\W+")
            .str.join(" ")
            .str.replace(r"(^|\s)(ST)\s", " SAINT ", regex=True)
            .str.replace(r"(^|\s)(STE)\s", " SAINTE ", regex=True)
            .str.replace(r"[0-9]* ?EME KM", "", regex=True)  # TAMPON 14EME KM
            .str.strip(" ")
            .str.replace(r" ?CEDEX$", "", regex=True)  # LOOS CEDEX -> LOOS
        )
        df = df.merge(unique, on=city, how="left")

    # Control which configuration can be used
    # Note that the order is relevant here, as this will determine the result's
    # preference
    to_test_ok = []
    to_test = [
        ((postcode, "city_cleaned"), "municipality"),
        ((address, postcode, "city_cleaned"), None),
        ((dep, "city_cleaned"), "municipality"),
    ]
    for test_cols, type_ban_search in to_test:
        try:
            df.loc[:, test_cols]
        except KeyError:
            pass
        else:
            to_test_ok.append((test_cols, type_ban_search))

    # Check that postcodes match 5 digits codes
    try:
        ix = df[df[postcode].notnull()].index
        if not (df.loc[ix, postcode].str.len() == 5).all():
            df.loc[ix, postcode] = df.loc[ix, postcode].str.zfill(5)
    except KeyError:
        pass

    components_kept = list(
        {field for test_cols, _ in to_test_ok for field in test_cols}
    )
    for f in components_kept:
        df[f] = df[f].replace("", np.nan)

    addresses = df.loc[:, components_kept + ["candidat_0"]].drop_duplicates()

    # Add dep recognition if not already there, just to check the result's
    # coherence (and NOT to compute city recognition using it!)
    drop_dep = False
    if not dep:
        drop_dep = True
        dep = "dep"
    try:
        if dep not in components_kept:
            addresses = find_departements(
                addresses,
                postcode,
                dep,
                "postcode",
                session,
                authorize_duplicates=True,
                threads=threads,
            )
    except KeyError:
        pass

    addresses = addresses.drop_duplicates(keep="first")

    # Where no results, check directly from INSEE's website for obsolete
    # cities (using dep & city) using fuzzy matching
    ix = addresses[addresses["candidat_0"].isnull()].index
    if len(ix) > 0:
        missing = (
            addresses.loc[ix, [dep, "city_cleaned"]]
            .rename({dep: "#dep#"}, axis=1)
            .drop_duplicates()
        )
        addresses = _find_from_fuzzymatch_cities_names(
            year,
            missing,
            "candidat_missing",
            addresses,
            dep,
            postcode,
            threads=threads,
        )

        addresses = addresses.drop_duplicates()

        candidats = ["candidat_0", "candidat_missing"]
        addresses["candidat_0"] = _combine(addresses, candidats)
        addresses = addresses.drop("candidat_missing", axis=1)

    for k, (components, type_ban_search) in enumerate(to_test_ok):
        cols_candidates = [
            x
            for x in addresses.columns
            if isinstance(x, str) and x.startswith("candidat_")
        ]

        ix = addresses[
            np.all(
                [addresses[col].isnull() for col in cols_candidates], axis=0
            )
            & np.all([addresses[col].notnull() for col in components], axis=0)
        ].index
        if len(ix) == 0:
            addresses[f"candidat_{k+1}"] = np.nan
            continue

        temp_addresses = addresses.loc[ix].drop(cols_candidates, axis=1)
        temp_addresses = temp_addresses.drop_duplicates().fillna("")

        def list_map(df, columns):
            # contatenation of multiple columns
            "https://stackoverflow.com/questions/39291499#answer-62135779"
            return pd.Series(
                map(" ".join, df[list(columns)].values.tolist()),
                index=df.index,
            )

        if "full" in set(temp_addresses.columns):
            temp_addresses = temp_addresses.drop("full", axis=1)
        temp_addresses = temp_addresses.join(
            list_map(temp_addresses.copy(), components).to_frame("full")
        )
        temp_addresses = temp_addresses.drop_duplicates("full", keep="first")

        if "full" in set(addresses.columns):
            addresses = addresses.drop("full", axis=1)
        addresses = addresses.join(
            list_map(addresses.fillna("").copy(), components).to_frame("full")
        )

        results_api = _query_BAN_csv_geocoder(
            addresses=temp_addresses,
            components=components,
            session=session,
            dep=dep,
            city="city_cleaned",
        )
        addresses = _filter_BAN_results(
            results_api=results_api,
            session=session,
            rename_candidat=f"candidat_{k+1}",
            addresses=addresses,
            dep=dep,
            threads=threads,
        )

        if type_ban_search == "municipality":
            try:
                addresses[f"candidat_{k+1}"]
            except KeyError:
                pass
            else:
                ix = addresses[
                    np.all(
                        [addresses[col].isnull() for col in cols_candidates],
                        axis=0,
                    )
                    & np.all(
                        [addresses[col].notnull() for col in components],
                        axis=0,
                    )
                    & (addresses[f"candidat_{k+1}"].isnull())
                ].index

                if len(ix) > 0:
                    # Try to use individual geocoding specifying target type
                    # (ie. "municipality" to get better results)

                    results_api = _query_BAN_individual_geocoder(
                        addresses=addresses.loc[ix],
                        components=components,
                        session=session,
                        dep=dep,
                        threads=threads,
                    )
                    addresses = _filter_BAN_results(
                        results_api=results_api,
                        session=session,
                        rename_candidat=f"candidat_{k+1}",
                        addresses=addresses,
                        dep=dep,
                        threads=threads,
                    )

    # Proceed in two steps to keep best result (in case there are results from
    # geolocation on lines with nothing other than coordinates)
    candidats = sorted(
        [x for x in addresses.columns if x.startswith("candidat")]
    )
    addresses["best"] = _combine(addresses, candidats)
    addresses = addresses.drop(candidats, axis=1)
    try:
        addresses = addresses.drop("full", axis=1)
    except KeyError:
        pass
    addresses = addresses.drop_duplicates(components_kept)

    df = df.merge(
        addresses.replace("", np.nan), how="left", on=components_kept
    )
    df["best"] = _combine(df, ["candidat_0", "best"])
    df = df.drop("candidat_0", axis=1)

    # Where still no results, give a go at individual requests through geopy
    # with Nominatim geocodage (if use_nominatim_backend set to True)
    ix = df[df["best"].isnull()].index
    if use_nominatim_backend and len(ix) > 0:

        # Cache pynsee adminexpress geodata
        logger.info("Retrieving adminexpress geodataframes with pynsee")
        cities = get_geodata("ADMINEXPRESS-COG-CARTO.LATEST:commune")
        cities = gpd.GeoDataFrame(cities).set_crs("EPSG:3857")
        logger.info("done")

        for use in [postcode, dep]:
            ix = df[df["best"].isnull()].index

            try:
                df[use]
            except KeyError:
                continue
            missing = df.loc[ix, [use, "city_cleaned"]]
            missing = missing.drop_duplicates(keep="first")
            missing["query"] = missing[use] + " " + missing["city_cleaned"]
            ix_empty_query = missing[missing["query"].isnull()].index
            missing = missing.drop(ix_empty_query)
            if missing.empty:
                continue
            missing = _find_with_nominatim_geolocation(
                year=year,
                look_for=missing[["query"]],
                alias="insee_com_nominatim",
                cities=cities,
                threads=threads,
            )
            if missing.empty:
                continue
            missing = find_departements(
                missing,
                source="insee_com_nominatim",
                alias="dep_nominatim",
                type_field="insee",
                threads=threads,
            )
            temp = df.loc[ix]
            temp["query"] = temp[use] + " " + temp["city_cleaned"]
            temp = temp.merge(missing, on="query")
            ix = temp[
                (temp["insee_com_nominatim"].notnull())
                & (temp[dep] == temp["dep_nominatim"])
            ].index
            temp = temp.loc[ix]
            df = df.merge(
                temp[[use, "city_cleaned", "insee_com_nominatim"]],
                on=[use, "city_cleaned"],
                how="left",
            )
            df["best"] = _combine(df, ["best", "insee_com_nominatim"])
            df = df.drop("insee_com_nominatim", axis=1)

    df = df.drop("city_cleaned", axis=1)
    df = df.rename({"best": field_output}, axis=1)

    if drop_dep:
        df = df.drop(dep, axis=1)

    df = df.set_index("#INDEX#")
    df.index.name = index_original_name
    return df


def _combine(df: pd.DataFrame, columns: list) -> pd.Series:
    """
    coalesce multiple columns (first not null encountered from left to right
    is kept) and return the result as pd.Series
    """

    columns = [x for x in columns if x in set(df.columns)]
    first, *next_ = columns
    s = df[first]
    for field in next_:
        with warnings.catch_warnings():
            warnings.simplefilter(action="ignore", category=FutureWarning)
            s = s.combine_first(df[field])
    return s


@lru_cache(maxsize=None)
def warn_nominatim():
    logger.warning(
        "Usage of Nominatim for geocoding is **NOT** encouraged. "
        "Please, have a look at the Geocoding Policy at "
        "https://operations.osmfoundation.org/policies/nominatim/ . "
    )


def _find_with_nominatim_geolocation(
    year: str,
    look_for: pd.DataFrame,
    alias: str,
    cities: gpd.GeoDataFrame,
    threads: int = THREADS,
) -> pd.DataFrame:
    """
    Use Nominatim API to geolocate rows of the dataframe. This can be a lengthy
    process.

    Parameters
    ----------
    year : str
        Desired vintage ("last" or castable to int)
    look_for : pd.DataFrame
        DataFrame cities (the queries will be performed on column "query") we
        are trying to find a match to
    alias : str
        field to use to store the positive matches' codes into the returned
        dataframe
    cities : gpd.GeoDataFrame
        Adminexpress geodataset retrieved with pynsee
    threads : int, optional
        Number of threads to use. Default is 10.

    Returns
    -------
    look_for : pd.DataFrame
        DataFrame of positive matches (ie look_for + one mor column under the
        label `alias`)

    """

    warn_nominatim()
    try:
        geolocator = Nominatim(user_agent=get_machine_user_agent())
    except NameError:
        logger.error(
            "geopy not installed - please install optional dependencies "
            "to use Nominatim geocoder with: pip install french-cities[full]"
        )
        return pd.DataFrame()

    cache_nominatim = diskcache.Cache(os.path.join(DIR_CACHE, "nominatim"))

    def french_cities_geocoder(x):
        try:
            ret = cache_nominatim[x]
        except KeyError:
            # Look first at settlements
            # doc : A featureType of settlement selects any human inhabited
            # feature from 'state' down to 'neighbourhood'.
            # https://nominatim.org/release-docs/latest/api/Search/
            ret = geolocator.geocode(
                x,
                language="fr",
                country_codes="fr",
                featuretype="settlement",
            )
            if not ret:
                # if no settlement found, search any kind of location
                time.sleep(1)
                ret = geolocator.geocode(
                    x,
                    language="fr",
                    country_codes="fr",
                )
            cache_nominatim.set(x, ret, expire=3600 * 24 * 30)
            logger.debug("Nominatim: new query, waiting !")
            time.sleep(1)
        return ret

    # deactivate the minimum delay as it is should be triggered inside
    # french_cities_geocoder
    func = RateLimiter(french_cities_geocoder, min_delay_seconds=0)

    estimated_time = len(look_for) / 60
    logger.warning(
        "Nominatim API will perform requests at a rate of one request "
        "per second : this task may take up to %s min "
        "(estimation without cache processing)...",
        round(estimated_time) + 1,
    )

    tqdm.pandas(desc="Querying Nominatim", leave=False)
    results = look_for["query"].progress_apply(func)

    cache_nominatim.close()

    look_for = look_for.assign(results=results)
    ix = look_for[look_for.results.notnull()].index
    for f in ["latitude", "longitude"]:
        look_for.loc[ix, f] = look_for.loc[ix, "results"].apply(
            lambda loc: getattr(loc, f)
        )
    logger.info("done with Nominatim")

    look_for = _find_from_geoloc(
        epsg=4326,
        df=look_for,
        year=year,
        x="longitude",
        y="latitude",
        field_output=alias,
        cities=cities,
        threads=threads,
    )
    look_for = look_for.drop(["latitude", "longitude", "results"], axis=1)
    return look_for


def _find_from_fuzzymatch_cities_names(
    year: str,
    look_for: pd.DataFrame,
    alias: str,
    addresses: pd.DataFrame,
    alias_dep: str,
    alias_postcode: str,
    threads: int = THREADS,
) -> pd.DataFrame:
    """
    Use fuzzy matching to retrieve cities from their names to find best
    candidates.

    Parameters
    ----------
    year : str
        Desired vintage ("last" or castable to int)
    look_for : pd.DataFrame
        DataFrame cities (expected columns are "city_cleaned" & "dep") we are
        trying to find a match to
    alias : str
        field to use to store the positive matches' codes into the returned
        dataframe
    addresses : pd.DataFrame
        original dataset with "full" addresses
    alias_dep : str
        field used to store the department's code in addresses
    alias_postcode : str
        field used to store the postcode in addresses
    threads : int, optional
        Number of threads to use. Default is 10.

    Returns
    -------
    match : pd.DataFrame
        DataFrame of positive matches (ie look_for + one mor column under the
        label `alias`)

    """
    init_pynsee()

    df = get_cities_and_ultramarines(date="*", threads=threads)
    df["TITLE_SHORT"] = (
        df["TITLE_SHORT"]
        .str.upper()
        .apply(unidecode)
        .str.split(r"\W+")
        .str.join(" ")
        .str.strip(" ")
    )
    df = df.loc[:, ["TITLE_SHORT", "CODE"]]

    df = find_departements(
        df,
        source="CODE",
        alias="dep",
        type_field="insee",
        do_set_vintage=False,
        threads=threads,
    )
    df = df.drop_duplicates(["TITLE_SHORT", "dep"])
    df = df.reset_index(drop=False)

    results = []
    desc = "fuzzy matching cities / dep"
    for dep in tqdm(look_for["#dep#"].unique(), desc=desc, leave=False):
        if not pd.isnull(dep):
            ix1 = look_for[look_for["#dep#"] == dep].index
            ix2 = df[df.dep == dep].index
        else:
            ix1 = look_for[look_for["#dep#"].isnull()].index
            ix2 = df.index
        match_ = pd.DataFrame(
            cdist(
                look_for.loc[ix1, "city_cleaned"],
                df.loc[ix2, "TITLE_SHORT"],
                score_cutoff=80,
                # scorer=fuzz.token_set_ratio,
                workers=1,  # Nota : workers=-1 currently crashes python
            ),
            index=ix1,
            columns=df.loc[ix2, ["TITLE_SHORT", "CODE"]],
        ).replace(0, np.nan)

        try:
            this_result = match_.dropna(how="all", axis=1).dropna(how="all")
            best = this_result.max(axis=1)
            # Keep only best results
            this_result = this_result.apply(lambda s: (s == best.values) * s)
            this_result = pd.Series(
                this_result.T.drop_duplicates(
                    keep=False
                )  # drop all equal scores
                .T.dropna(how="all")
                .idxmax(axis=1),
                index=ix1,
            )
            this_result = this_result.dropna()
            results.append(this_result)
        except ValueError:
            pass

        # If no result with simple ratio, use WRatio
        ix1 = list(set(ix1) - set(this_result.index))

        match_ = pd.DataFrame(
            cdist(
                look_for.loc[ix1, "city_cleaned"],
                df.loc[ix2, "TITLE_SHORT"],
                score_cutoff=90,
                scorer=fuzz.WRatio,
                workers=1,  # Nota : workers=-1 currently crashes python
            ),
            index=ix1,
            columns=df.loc[ix2, ["TITLE_SHORT", "CODE"]],
        ).replace(0, np.nan)

        try:
            this_result = match_.dropna(how="all", axis=1).dropna(how="all")
            best = this_result.max(axis=1)
            # Keep only best results
            this_result = this_result.apply(lambda s: (s == best.values) * s)
            this_result = pd.Series(
                this_result.T.drop_duplicates(
                    keep=False
                )  # drop all equal scores
                .T.dropna(how="all")
                .idxmax(axis=1),
                index=ix1,
            )
            this_result = this_result.dropna()
            results.append(this_result)
        except ValueError:
            continue

    results = [x for x in results if not x.empty]
    try:
        results = pd.concat(results, ignore_index=False).sort_index()
    except ValueError:
        # No objects to concatenate
        addresses[alias] = np.nan
    else:
        results = results.str[1]

        results = look_for.join(results.to_frame("CODE"))
        results = results.rename({"#dep#": alias_dep}, axis=1)

        if alias_postcode:
            results = addresses[
                [alias_postcode, alias_dep, "city_cleaned"]
            ].merge(results, on=[alias_dep, "city_cleaned"], how="left")
            results = _cleanup_results(
                results, alias_postcode=alias_postcode, threads=threads
            )
        else:
            pass

        try:
            year = int(year)
        except ValueError:
            year = date.today().year
        results = set_vintage(results, year, "CODE", threads=threads)

        # inner join (previous link at line 811 was of type left and
        # _cleanup_results did remove unwanted duplicates)
        if alias_postcode:
            addresses = addresses.merge(
                results,
                on=[alias_postcode, alias_dep, "city_cleaned"],
                how="inner",
            )
        else:
            addresses = results

    addresses = addresses.rename({"CODE": alias}, axis=1)
    return addresses


def _find_from_geoloc(
    epsg: int,
    df: pd.DataFrame,
    year: str = "last",
    x: str = "x",
    y: str = "y",
    field_output: str = "insee_com",
    cities: gpd.GeoDataFrame = None,
    threads: int = THREADS,
) -> pd.DataFrame:
    """
    Find cities codes from coordinates using a spatial join.

    Note that the result will be approximative as the IGN's WFS data is not
    vintaged (yet ?). The spatial join will then be computed against latest
    available data. A reprojection in the desired vintage will be done
    afterwards, but cities joined during this lapse time will NOT be correctly
    found.

    Parameters
    ----------
    epsg : int
        EPSG code of projection
    df : pd.DataFrame
        input DataFrame. Must have an 'x' and an 'y' columns containing points
    year : str, optional
        Desired vintage for cities; must a castable value to int or "last".
        The default is "last".
    x : str, optional
        Field (column) containing the x coordinates values. Set to False if
        not available. The default is "x".
    y : str, optional
        Field (column) containing the y coordinates values. Set to False if
        not available. The default is "y".
    field_output : str, optional
        Column to store the cities code into. The default is "insee_com".
    cities : gpd.GeoDataFrame, optional
        Adminexpress geodataset retrieved with pynsee. If None, will be
        retrieved later on. None by default.
    threads : int, optional
        Number of threads to use. Default is 10.

    Raises
    ------
    ValueError
        If year not castable to int, or not "last".

    Returns
    -------
    df : pd.DataFrame
        output DataFrame with `field_output` containing cities' codes

    """

    logger.info("find city through geolocation...")

    if year != "last":
        try:
            int(year)
        except ValueError as exc:
            raise ValueError(
                "year should either be castable to int or 'last', "
                f"found {year} instead"
            ) from exc

    if str(year) not in {str(date.today().year), "last"}:
        logger.warning(
            "As of yet, ADMINEXPRESS can't be fetched with a vintage "
            "setting: the querying of cities using coordinates WILL have "
            "approximative results."
        )

    if cities is None:
        cities = get_geodata("ADMINEXPRESS-COG-CARTO.LATEST:commune")
        cities = gpd.GeoDataFrame(cities).set_crs("EPSG:3857")

    transformer = Transformer.from_crs(epsg, 3857, accuracy=1, always_xy=True)

    temp = transformer.transform(df[x].tolist(), df[y].tolist())
    temp = gpd.GeoSeries(
        gpd.points_from_xy(x=temp[0], y=temp[1], crs=3857),
        name="geometry",
        index=df.index,
    )

    df = gpd.GeoDataFrame(temp.to_frame().join(df), crs=3857)
    rename = {"insee_com": field_output}
    df = df.sjoin(
        cities[["insee_com", "geometry"]].rename(rename, axis=1), how="left"
    )
    df = df.drop(["geometry", "index_right"], axis=1)

    if year not in {str(date.today().year), "last"}:
        year = int(year)
        df = set_vintage(df, year, field_output, threads=threads)
    return df


def _query_BAN_csv_geocoder(
    addresses: pd.DataFrame,
    components: list,
    session: Session,
    dep: str,
    city: str,
) -> pd.DataFrame:
    """
    Query the adresse API (BAN = Base Adresse Nationale) CSV geocoder.

    Parameters
    ----------
    addresses : pd.DataFrame
        Addresses to query the API from.
    components : list
        List of components used for constituting the addresses (used for
        debugging purposes only)
    session : Session
        Web session
    dep : str
        Column label containing the departements' codes
    city : str
        Column label containing the cities' labels

    Returns
    -------
    results_api : pd.DataFrame
        DataFrame (same as original + columns ['result_score', 'result_city',
        'result_citycode'])

    """
    # Use the BAN's CSV geocoder
    logger.info("request BAN with CSV geocoder and %s...", components)

    files = [
        ("data", addresses.to_csv(index=False)),
        # erratic behaviour of BAN API, deactivate type filtering for now
        # ("type", (None, "municipality")),
        ("result_columns", (None, "full")),
        ("result_columns", (None, "result_score")),
        ("result_columns", (None, "result_city")),
        ("result_columns", (None, "result_citycode")),
        ("result_columns", (None, "result_type")),
    ]

    # awaiting new API managed by IGN
    # see https://guides.data.gouv.fr/reutiliser-des-donnees/prendre-en-main-lapi-adresse-portee-par-lign#utilisation-de-lapi-adresse-portee-par-lign-et-les-differences-avec-lapi-adresse-portee-par-la-dinum
    r = session.post(
        "https://api-adresse.data.gouv.fr/search/csv/",
        files=files,
    )
    if not r.ok:
        raise Exception(
            f"Failed to query BAN's API with {files=} - response was {r}"
        )

    logger.info("résultat obtenu")

    try:
        results_api = (
            pd.read_csv(
                io.BytesIO(r.content),
                dtype={"dep": str, "result_citycode": str},
            )
            .drop_duplicates()
            .loc[
                :,
                ["full", "result_score", "result_city", "result_citycode"],
            ]
            .merge(
                addresses[[dep, "full", city]].drop_duplicates(),
                on="full",
            )
        )
    except Exception as exc:
        raise ValueError(
            "Failed to parse BAN's return with following content :\n\n"
            f"{r.content}"
        ) from exc
    return results_api


def _query_BAN_individual_geocoder(
    addresses: pd.DataFrame,
    components: list,
    session: Session,
    dep: str,
    threads: int = THREADS,
) -> pd.DataFrame:
    """
    Query the adresse API (BAN = Base Adresse Nationale) individual geocoder,
    specifying the output type as municipality (this parameter being not
    available through the CSV mass geocoder). Uses multithreading as no
    quota are not used by this API.

    Parameters
    ----------
    addresses : pd.DataFrame
        Addresses to query the API from.
    components : list
        List of components used for constituting the addresses (used for
        debugging purposes only)
    session : Session
        Web session
    dep : str
        Column label containing the departements' codes
    threads : int, optional
        Number of threads to use. Default is 10.

    Returns
    -------
    results_api : pd.DataFrame
        DataFrame (same as original + columns ['result_score', 'result_city',
        'result_citycode'])

    """
    # Use the BAN's individual geocoder

    # revert to multiple queries of BAN, see issue here:
    # https://github.com/BaseAdresseNationale/adresse.data.gouv.fr/issues/1575
    logger.info("request BAN with individual requests and %s...", components)

    def get(x):
        r = session.get(
            "https://data.geopf.fr/geocodage/search/",
            params={
                "q": x,
                "type": "municipality",
                "autocomplete": 0,
                "limit": 1,
            },
        ).json()
        try:
            features = r["features"]
        except KeyError:
            logger.error("query was q=%s", x)
            logger.error(r)
            raise

        try:
            query = r["query"]
        except KeyError:
            query = x
        for dict_ in features:
            dict_["properties"].update({"full": query})

        return features

    args = addresses.full.str.replace(r"\W+", " ", regex=True).tolist()
    results = []
    with tqdm(total=len(args), desc="Queuing download", leave=False) as pbar:
        with ThreadPool(threads) as pool:
            future = pool.map(get, args)
            results_iterator = future.result()
            while True:
                try:
                    this_result = next(results_iterator)
                    if this_result:
                        results.append(this_result)
                except StopIteration:
                    break
                finally:
                    pbar.update(1)

    logger.info("results collected")

    results_api = (
        gpd.GeoDataFrame.from_features(np.array(results).flatten())
        .loc[:, ["full", "score", "city", "citycode"]]
        .rename(
            {
                "score": "result_score",
                "city": "result_city",
                "citycode": "result_citycode",
            },
            axis=1,
        )
        .merge(
            addresses[[dep, "full", "city_cleaned"]].drop_duplicates(),
            on="full",
        )
    )
    return results_api


def _filter_BAN_results(
    results_api: pd.DataFrame,
    session: Session,
    rename_candidat: str,
    addresses: pd.DataFrame,
    dep: str = "dep",
    fuzzymatch_threshold: int = 80,
    ban_score_threshold_city_known: float = 0.6,
    ban_score_threshold_city_unknown: float = 0.4,
    threads: int = THREADS,
) -> pd.DataFrame:
    """
    Filters the BAN results to keep best results according to specific
    criteria. Results will be kept if :
        - they match expected departement
        - and :
            * if you get a good fuzzy match on city name
            * or if the BAN gives a good score, the city label being known
            * or if the BAN gives a goodish score, the city label being unknown

    Parameters
    ----------
    results_api : pd.DataFrame
        Adresse API results
    session : Session
        Web session
    rename_candidat : str
        Columnn to rename the results to.
    addresses : pd.DataFrame
        Full DataFrame of address to store the kept results into.
    dep : str, optional
        Field (column) containing the department values. Set to False if
        not available. The default is "dep".
    fuzzymatch_threshold : int, optional
        The fuzzy match score threshold (on city labels) to keep the results.
        Default is 80.
    ban_score_threshold_city_known : float, optional
        The API score threshold to keep results, the city label being known.
        Default is 0.6.
    ban_score_threshold_city_unknown : float, optional
        The API score threshold to keep results, the city label being unknown.
        Default is 0.4.
    threads : int, optional
        Number of threads to use. Default is 10.

    Returns
    -------
    addresses : pd.DataFrame
        Consolidated DataFrame of address with selected results.

    """
    # Control results : same department
    results_api = find_departements(
        results_api,
        "result_citycode",
        "result_dep",
        "insee",
        session,
        threads=threads,
    )
    ix = results_api[results_api[dep] == results_api.result_dep].index
    results_api = results_api.loc[ix]

    if results_api.empty:
        return addresses

    # Control result : fuzzy matching on city label
    results_api["result_city"] = (
        results_api["result_city"]
        .str.upper()
        .apply(unidecode)
        .str.split(r"\W+")
        .str.join(" ")
    )
    results_api["score"] = results_api[["city_cleaned", "result_city"]].apply(
        lambda xy: fuzz.token_set_ratio(*xy), axis=1
    )

    ix = results_api[
        # Either a good fuzzy match
        (
            (results_api["city_cleaned"] != "")
            & (results_api["score"] > fuzzymatch_threshold)
        )
        # Or a goodish match on BAN (case of cities fusion, city
        # neighborhoods, ski stations...):
        | (
            (results_api["city_cleaned"] != "")
            & (results_api["result_score"] > ban_score_threshold_city_known)
        )
        # Or a goodish match on BAN but no available city label:
        | (
            (results_api["city_cleaned"] == "")
            & (results_api["result_score"] > ban_score_threshold_city_unknown)
        )
    ].index

    if rename_candidat in addresses.columns:
        results_api = results_api.loc[ix, ["full", "result_citycode"]]
        addresses = addresses.merge(results_api, on="full", how="left")
        ix = addresses[addresses.result_citycode.notnull()].index
        addresses.loc[ix, rename_candidat] = addresses.loc[
            ix, "result_citycode"
        ]
        addresses = addresses.drop("result_citycode", axis=1)

    else:
        results_api = results_api.loc[ix, ["full", "result_citycode"]].rename(
            {"result_citycode": rename_candidat}, axis=1
        )
        addresses = addresses.merge(results_api, on="full", how="left")
    return addresses
