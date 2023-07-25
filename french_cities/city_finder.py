# -*- coding: utf-8 -*-
"""
Created on Thu Jul  6 11:38:34 2023
"""
import pandas as pd
import io
import logging
from requests_cache import CachedSession
from requests import Session
from rapidfuzz import fuzz
from unidecode import unidecode
from pynsee.geodata import get_geodata
from pynsee.localdata import get_area_list
import geopandas as gpd
from pyproj import Transformer
from datetime import date, timedelta
from typing import Union
import numpy as np
from pebble import ThreadPool
from tqdm import tqdm

from french_cities.vintage import set_vintage
from french_cities.departement_finder import find_departements
from french_cities.utils import init_pynsee


logger = logging.getLogger(__name__)


def _fuzzy_match_cities_names(
    year: str, look_for: pd.DataFrame, alias: str
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
        datafram

    Returns
    -------
    match : pd.DataFrame
        DataFrame of positive matches (ie look_for + one mor column under the
        label `alias`)

    """
    init_pynsee()

    df = get_area_list("communes", date="*")
    df["TITLE_SHORT"] = (
        df["TITLE_SHORT"]
        .str.upper()
        .apply(unidecode)
        .str.split(r"\W+")
        .str.join(" ")
        .str.strip(" ")
    )
    df = df.loc[:, ["TITLE_SHORT", "CODE"]]

    df = find_departements(df, source="CODE", alias="dep", type_code="insee")
    df = df.drop_duplicates(["TITLE_SHORT", "dep"])
    df = df.reset_index(drop=False)

    # fuzzy matching df / look_for
    match_ = look_for.merge(df, on="dep", how="inner")
    match_["fuzzy_match"] = match_[["city_cleaned", "TITLE_SHORT"]].apply(
        lambda xy: fuzz.token_set_ratio(*xy), axis=1
    )

    ix = match_[match_.fuzzy_match > 80].index
    match_ = match_.loc[ix]

    # Keep matches only best match in case of ambiguity
    match_ = match_.sort_values("fuzzy_match", ascending=False)
    match_ = match_.drop_duplicates("city_cleaned", keep="first")
    match_ = match_.drop("fuzzy_match", axis=1)

    try:
        year = int(year)
    except ValueError:
        year = date.today().year
    match_ = set_vintage(match_, year, "CODE")
    match_ = look_for.merge(
        match_[["city_cleaned", "dep", "CODE"]],
        on=["city_cleaned", "dep"],
        how="left",
    )
    match_ = match_.rename({"CODE": alias}, axis=1)
    return match_


def _find_from_geoloc(
    epsg: int,
    df: pd.DataFrame,
    year: str = "last",
    x: str = "x",
    y: str = "y",
    field_output: str = "insee_com",
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
        except ValueError:
            raise ValueError(
                "year should either be castable to int or 'last', "
                f"found {year} instead"
            )

    if str(year) not in {str(date.today().year), "last"}:
        logger.warning(
            "As of yet, ADMINEXPRESS can't be fetched with a vintage "
            "setting: the querying of cities using coordinates WILL have "
            "approximative results."
        )

    com = get_geodata("ADMINEXPRESS-COG-CARTO.LATEST:commune")
    com = gpd.GeoDataFrame(com).set_crs("EPSG:3857")

    transformer = Transformer.from_crs(epsg, 3857, accuracy=1, always_xy=True)

    temp = transformer.transform(df[x].tolist(), df[y].tolist())
    temp = gpd.GeoSeries(
        gpd.points_from_xy(x=temp[0], y=temp[1], crs=3857),
        name="geometry",
        index=df.index,
    )

    df = gpd.GeoDataFrame(temp.to_frame().join(df), crs=3857)
    df = df.sjoin(com[["insee_com", "geometry"]], how="left")
    df = df.drop(["geometry", "index_right"], axis=1)

    if year not in {str(date.today().year), "last"}:
        year = int(year)
        df = set_vintage(df, year, "insee_com")
    return df


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
        - postcode + city label
        - address + postcode + city label
        - department + city label

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

    if year != "last":
        try:
            int(year)
        except ValueError:
            raise ValueError(
                "year should either be castable to int or 'last', "
                f"found {year} instead"
            )

    columns = set(df.columns)
    necessary1 = {postcode, city}
    necessary2 = {dep, city}
    necessary3 = {x, y}
    if not any(
        len(conf - columns) == 0
        for conf in (necessary1, necessary2, necessary3)
    ):
        msg = (
            f"All columns among {necessary1}, {necessary2} OR {necessary3} "
            "are necessary"
        )
        raise ValueError(msg)

    init_pynsee()

    if not session:
        session = CachedSession(
            allowable_methods=("GET", "POST"), expire_after=timedelta(days=30)
        )

    if len(necessary3 - columns) == 0 and not epsg:
        logger.warning(
            "x and y columns where found, but a valid EPSG projection was not "
            "set : geolocation will not be performed"
        )

    # User geolocation first
    elif len(necessary3 - columns) == 0 and epsg:
        # On peut travailler à partir de la géoloc
        df = _find_from_geoloc(epsg, df, year, x, y, field_output).rename(
            {field_output: "candidat_0"}, axis=1
        )

    # Preprocess cities names
    if city in set(df.columns):
        df["city_cleaned"] = (
            df[city]
            .str.replace(
                r" \(.*\)$", "", regex=True
            )  # Neuville-Housset (La) -> Neuville-Housset
            .str.upper()
            .apply(unidecode)  # A voir si on conserve
            .str.split(r"\W+")
            .str.join(" ")
            .str.strip(" ")
            .str.replace(r" ?CEDEX$", "", regex=True)  # LOOS CEDEX -> LOOS
        )

    # Control which configuration can be used
    # Note that the order is relevant here, as this will determine the result's
    # preference
    to_test_ok = {}
    to_test = {
        (postcode, "city_cleaned"): "municipality",
        (address, postcode, "city_cleaned"): None,
        (dep, "city_cleaned"): "municipality",
    }
    for test_cols, type_ban_search in to_test.items():
        try:
            df.loc[:, test_cols]
        except KeyError:
            pass
        else:
            to_test_ok[test_cols] = type_ban_search

    components_kept = list(
        {field for test_cols in to_test_ok for field in test_cols}
    )

    addresses = df.loc[:, components_kept].drop_duplicates().fillna("")

    # Add dep recognition if not already there, just to check the result's
    # coherence (and NOT to compute city recognition using it!)
    if dep not in components_kept:
        addresses = find_departements(
            addresses, postcode, dep, "postcode", session
        )

    for k, components in enumerate(to_test_ok):

        def list_map(df, columns):
            # contatenation of multiple columns
            "https://stackoverflow.com/questions/39291499#answer-62135779"
            return pd.Series(
                map(" ".join, df[list(columns)].values.tolist()),
                index=df.index,
            )

        if "full" in set(addresses.columns):
            addresses = addresses.drop("full", axis=1)
        addresses = addresses.join(
            list_map(addresses.copy(), components).to_frame("full")
        )
        addresses = addresses.drop_duplicates(keep="first")

        if to_test_ok[components] is None:
            # safe to use the CSV geocoder
            logger.info(f"request BAN with CSV geocoder and {components}...")
            r = session.post(
                # recherche "en masse" grâce à l'API de la BAN
                "https://api-adresse.data.gouv.fr/search/csv/",
                files=[
                    ("data", addresses.to_csv(index=False)),
                    ("type", (None, "municipality")),
                    ("result_columns", (None, "full")),
                    ("result_columns", (None, "result_score")),
                    ("result_columns", (None, "result_city")),
                    ("result_columns", (None, "result_citycode")),
                ],
            )

            logger.info("résultat obtenu")

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
                    addresses[[dep, "full", "city_cleaned"]].drop_duplicates(),
                    on="full",
                )
            )

        else:
            # revert to multiple queries of BAN, see issue here:
            # https://github.com/BaseAdresseNationale/adresse.data.gouv.fr/issues/1575
            logger.info(
                f"request BAN with individual requests and {components}..."
            )

            def get(x):
                r = session.get(
                    # recherche "en masse" grâce à l'API de la BAN
                    "https://api-adresse.data.gouv.fr/search/",
                    params={
                        "q": x,
                        "type": to_test_ok[components],
                        "autocomplete": 0,
                        "limit": 1,
                    },
                ).json()
                features = r["features"]
                query = r["query"]
                for dict_ in features:
                    dict_["properties"].update({"full": query})

                return features

            # Without multithreading:
            # results_api = gpd.GeoDataFrame.from_features(
            #     np.array(addresses.full.apply(get).tolist()).flatten()
            #     )

            args = addresses.full.tolist()
            results = []
            with tqdm(
                total=len(args), desc="Queuing download", leave=False
            ) as pbar:
                with ThreadPool(10) as pool:
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

            logger.info("résultat obtenu")

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

        # Control results : same department
        results_api = find_departements(
            results_api, "result_citycode", "result_dep", "insee", session
        )
        ix = results_api[results_api.dep == results_api.result_dep].index
        results_api = results_api.loc[ix]

        # Control result : fuzzy matching on city label
        results_api["result_city"] = (
            results_api["result_city"]
            .str.upper()
            .apply(unidecode)
            .str.split(r"\W+")
            .str.join(" ")
        )
        results_api["score"] = results_api[
            ["city_cleaned", "result_city"]
        ].apply(lambda xy: fuzz.token_set_ratio(*xy), axis=1)

        ix = results_api[
            # Either a good fuzzy match
            ((results_api["city_cleaned"] != "") & (results_api["score"] > 80))
            # Or a good match on BAN (case of cities fusion for instance):
            | (results_api["city_cleaned"] != "")
            & (results_api["result_score"] > 0.6)
            # Or a goodish match on BAN but no available city label:
            | (results_api["city_cleaned"] == "")
            & (results_api["result_score"] > 0.4)
        ].index

        results_api = results_api.loc[ix, ["full", "result_citycode"]].rename(
            {"result_citycode": f"candidat_{k+1}"}, axis=1
        )
        addresses = addresses.merge(results_api, on="full", how="left")

    def combine(df: pd.DataFrame, columns: list) -> pd.Series:
        columns = [x for x in columns if x in set(df.columns)]
        first, *next_ = columns
        s = df[first]
        for field in next_:
            s = s.combine_first(df[field])
        return s

    candidats = [f"candidat_{k+1}" for k in range(len(to_test_ok))]
    addresses["best"] = combine(addresses, candidats)
    addresses = addresses.drop(candidats, axis=1)
    addresses = addresses.drop("full", axis=1)
    addresses = addresses.drop_duplicates()

    df = (
        df
        .reset_index(drop=False)
        .merge(
            addresses.replace("", np.nan), how="left", on=components_kept
        )
    )
    candidats = ["candidat_0", "best"]
    df[field_output] = combine(df, candidats)
    df = df.drop(
        [x for x in candidats if x in set(df.columns)],
        axis=1,
    )

    # Where still no results, check directly from INSEE's website for obsolete
    # cities (using dep & city)
    ix = df[df[field_output].isnull()].index
    if len(ix) > 0:
        missing = df.loc[ix, [dep, "city_cleaned"]]
        missing = _fuzzy_match_cities_names(year, missing, "candidat_missing")
        df = df.merge(missing, on=[dep, "city_cleaned"], how="left")

        candidats = [field_output, "candidat_missing"]
        df[field_output] = combine(df, candidats)
        df = df.drop("candidat_missing", axis=1)

    df = df.drop("city_cleaned", axis=1)
    df = df.set_index("index")
    return df
