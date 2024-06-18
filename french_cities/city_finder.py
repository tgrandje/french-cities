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
from rapidfuzz.process import cdist
from unidecode import unidecode
from pynsee.geodata import get_geodata
from pynsee.localdata import get_area_list
import geopandas as gpd
from pyproj import Transformer
from datetime import date, timedelta
from typing import Union
import numpy as np
from functools import partial
from uuid import uuid4
from tqdm import tqdm
from pebble import ThreadPool

try:
    from geopy.extra.rate_limiter import RateLimiter
    from geopy.geocoders import Nominatim
except ModuleNotFoundError:
    pass


from french_cities.vintage import set_vintage
from french_cities.departement_finder import find_departements
from french_cities.utils import init_pynsee, patch_the_patch


logger = logging.getLogger(__name__)


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
            allowable_methods=("GET", "POST"),
            expire_after=timedelta(days=30),
        )

    if len(necessary3 - columns) == 0 and not epsg:
        logger.warning(
            "x and y columns where found, but a valid EPSG projection was not "
            "set: geolocation will not be performed"
        )

    # User geolocation first
    elif len(necessary3 - columns) == 0 and epsg:
        # On peut travailler à partir de la géoloc
        df = _find_from_geoloc(epsg, df, year, x, y, field_output).rename(
            {field_output: "candidat_0"}, axis=1
        )
    try:
        df["candidat_0"]
    except KeyError:
        df = df.assign(candidat_0=np.nan)

    # Preprocess cities names
    if city in set(df.columns):
        ix = df[(df[city].notnull()) & (df.candidat_0.isnull())].index
        df.loc[ix, "city_cleaned"] = (
            df.loc[ix, city]
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
                addresses, postcode, dep, "postcode", session
            )
    except KeyError:
        pass

    # Where no results, check directly from INSEE's website for obsolete
    # cities (using dep & city) using fuzzy matching
    ix = addresses[addresses["candidat_0"].isnull()].index
    if len(ix) > 0:
        missing = addresses.loc[ix, [dep, "city_cleaned"]].rename(
            {dep: "#dep#"}, axis=1
        )
        missing = _find_from_fuzzymatch_cities_names(
            year, missing, "candidat_missing"
        ).rename({"#dep#": dep}, axis=1)
        addresses = addresses.merge(
            missing, on=[dep, "city_cleaned"], how="left"
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
        )
        addresses = _filter_BAN_results(
            results_api=results_api,
            session=session,
            rename_candidat=f"candidat_{k+1}",
            addresses=addresses,
            dep=dep,
        )

        if type_ban_search == "municipality":
            ix = addresses[
                np.all(
                    [addresses[col].isnull() for col in cols_candidates],
                    axis=0,
                )
                & np.all(
                    [addresses[col].notnull() for col in components], axis=0
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
                )
                addresses = _filter_BAN_results(
                    results_api=results_api,
                    session=session,
                    rename_candidat=f"candidat_{k+1}",
                    addresses=addresses,
                    dep=dep,
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

    df = df.reset_index(drop=False).merge(
        addresses.replace("", np.nan), how="left", on=components_kept
    )
    df["best"] = _combine(df, ["candidat_0", "best"])
    df = df.drop("candidat_0", axis=1)

    # Where still no results, give a go at individual requests through geopy
    # with Nominatim geocodage (if use_nominatim_backend set to True)
    ix = df[df["best"].isnull()].index
    if use_nominatim_backend and len(ix) > 0:
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
            )
            if missing.empty:
                continue
            missing = find_departements(
                missing,
                source="insee_com_nominatim",
                alias="dep_nominatim",
                type_code="insee",
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

    df = df.set_index("index")
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
        s = s.combine_first(df[field])
    return s


def _find_with_nominatim_geolocation(
    year: str, look_for: pd.DataFrame, alias: str
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

    Returns
    -------
    look_for : pd.DataFrame
        DataFrame of positive matches (ie look_for + one mor column under the
        label `alias`)

    """

    logger.info(
        "Please read Nominatim Usage Policy at "
        "https://operations.osmfoundation.org/policies/nominatim/"
    )
    user_agent = f"french-cities-{uuid4()}"
    try:
        geolocator = Nominatim(user_agent=user_agent)
    except NameError:
        logger.error(
            "geopy not installed - please install optional dependencies "
            "to use Nominatim geocoder with: pip install french-cities[full]"
        )
        return pd.DataFrame()

    geocode = RateLimiter(
        partial(
            geolocator.geocode,
            language="fr",
            country_codes="fr",
            featuretype="settlement ",
        ),
        min_delay_seconds=1,
    )

    logger.info(
        "Nominatim API will perform requests at a rate of one request "
        f"per second : this task will need around {len(look_for)}s."
    )

    results = look_for["query"].apply(geocode)
    look_for = look_for.assign(results=results)
    ix = look_for[look_for.results.notnull()].index
    for f in ["latitude", "longitude"]:
        look_for.loc[ix, f] = look_for.loc[ix, "results"].apply(
            lambda loc: getattr(loc, f)
        )

    look_for = _find_from_geoloc(
        epsg=4326,
        df=look_for,
        year=year,
        x="longitude",
        y="latitude",
        field_output=alias,
    )
    look_for = look_for.drop(["latitude", "longitude", "results"], axis=1)
    return look_for


def _find_from_fuzzymatch_cities_names(
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

    results = []
    for dep in look_for["#dep#"].unique():
        ix1 = look_for[look_for["#dep#"] == dep].index
        ix2 = df[df.dep == dep].index
        match_ = pd.DataFrame(
            cdist(
                look_for.loc[ix1, "city_cleaned"],
                df.loc[ix2, "TITLE_SHORT"],
                score_cutoff=80,
                workers=-1,
            ),
            index=ix1,
            columns=df.loc[ix2, ["TITLE_SHORT", "CODE"]],
        ).replace(0, np.nan)

        try:
            results.append(
                pd.Series(
                    match_.dropna(how="all", axis=1)
                    .dropna(how="all")
                    .idxmax(axis=1),
                    index=ix1,
                )
            )
        except ValueError:
            continue

    results = pd.concat(results, ignore_index=False).sort_index()
    results = results.str[1]
    try:
        year = int(year)
    except ValueError:
        year = date.today().year
    results = set_vintage(results.to_frame("CODE"), year, "CODE")

    results = look_for.join(results)

    results = results.rename({"CODE": alias}, axis=1)
    return results


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
    rename = {"insee_com": field_output}
    df = df.sjoin(
        com[["insee_com", "geometry"]].rename(rename, axis=1), how="left"
    )
    df = df.drop(["geometry", "index_right"], axis=1)

    if year not in {str(date.today().year), "last"}:
        year = int(year)
        df = set_vintage(df, year, field_output)
    return df


def _query_BAN_csv_geocoder(
    addresses: pd.DataFrame,
    components: list,
    session: Session,
    dep: str,
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

    Returns
    -------
    results_api : pd.DataFrame
        DataFrame (same as original + columns ['result_score', 'result_city',
        'result_citycode'])

    """
    # Use the BAN's CSV geocoder
    logger.info(f"request BAN with CSV geocoder and {components}...")

    files = [
        ("data", addresses.to_csv(index=False)),
        ("type", (None, "municipality")),
        ("result_columns", (None, "full")),
        ("result_columns", (None, "result_score")),
        ("result_columns", (None, "result_city")),
        ("result_columns", (None, "result_citycode")),
    ]

    with patch_the_patch():
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
                addresses[[dep, "full", "city_cleaned"]].drop_duplicates(),
                on="full",
            )
        )
    except Exception:
        raise ValueError(
            "Failed to parse BAN's return with following content :\n\n"
            f"{r.content}"
        )
    return results_api


def _query_BAN_individual_geocoder(
    addresses: pd.DataFrame,
    components: list,
    session: Session,
    dep: str,
    threads: int = 10,
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
    logger.info(f"request BAN with individual requests and {components}...")

    def get(x):
        r = session.get(
            "https://api-adresse.data.gouv.fr/search/",
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
            logger.error(f"query was q={x}")
            logger.error(r)
            raise

        query = r["query"]
        for dict_ in features:
            dict_["properties"].update({"full": query})

        return features

    # Without multithreading:
    # results_api = gpd.GeoDataFrame.from_features(
    #     np.array(addresses.full.apply(get).tolist()).flatten()
    #     )

    args = addresses.full.str.replace("\W", "", regex=True).tolist()
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

    Returns
    -------
    addresses : pd.DataFrame
        Consolidated DataFrame of address with selected results.

    """
    # Control results : same department
    results_api = find_departements(
        results_api, "result_citycode", "result_dep", "insee", session
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
