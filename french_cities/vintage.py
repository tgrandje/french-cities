# -*- coding: utf-8 -*-
"""
Created on Fri Jul  7 09:17:12 2023

Module used to project a dataset into a known vintage, wether the original
vintage is known or not.
"""
from datetime import date, datetime
import os
from functools import partial
import logging

import diskcache
import pandas as pd
from pebble import ThreadPool

from pynsee.localdata import get_area_list
from pynsee.localdata import get_ascending_area
from pynsee.localdata import get_area_projection
from tqdm import tqdm

from french_cities import DIR_CACHE
from french_cities.constants import THREADS
from french_cities.utils import init_pynsee, silence_sirene_logs
from french_cities.ultramarine_pseudo_cog import get_cities_and_ultramarines


logger = logging.getLogger(__name__)


cache_projection = diskcache.Cache(os.path.join(DIR_CACHE, "projection"))

FIXED_ULTRAMARINE_CODES = {
    # Saint-Pierre-et-Miquelon
    "97501": "97501",
    "97502": "97502",
    # Terres australes et antarctiques françaises
    "98411": "98411",
    "98412": "98412",
    "98413": "98413",
    "98414": "98414",
    "98415": "98415",
    # Wallis-et-Futuna
    "98611": "98611",
    "98612": "98612",
    "98613": "98613",
    # Polynésie française
    "98711": "98711",
    "98712": "98712",
    "98713": "98713",
    "98714": "98714",
    "98715": "98715",
    "98716": "98716",
    "98717": "98717",
    "98718": "98718",
    "98719": "98719",
    "98720": "98720",
    "98721": "98721",
    "98722": "98722",
    "98723": "98723",
    "98724": "98724",
    "98725": "98725",
    "98726": "98726",
    "98727": "98727",
    "98728": "98728",
    "98729": "98729",
    "98730": "98730",
    "98731": "98731",
    "98732": "98732",
    "98733": "98733",
    "98734": "98734",
    "98735": "98735",
    "98736": "98736",
    "98737": "98737",
    "98738": "98738",
    "98739": "98739",
    "98740": "98740",
    "98741": "98741",
    "98742": "98742",
    "98743": "98743",
    "98744": "98744",
    "98745": "98745",
    "98746": "98746",
    "98747": "98747",
    "98748": "98748",
    "98749": "98749",
    "98750": "98750",
    "98751": "98751",
    "98752": "98752",
    "98753": "98753",
    "98754": "98754",
    "98755": "98755",
    "98756": "98756",
    "98757": "98757",
    "98758": "98758",
    # Nouvelle-Calédonie
    "98801": "98801",
    "98802": "98802",
    "98803": "98803",
    "98804": "98804",
    "98805": "98805",
    "98806": "98806",
    "98807": "98807",
    "98808": "98808",
    "98809": "98809",
    "98810": "98810",
    "98811": "98811",
    "98812": "98812",
    "98813": "98813",
    "98814": "98814",
    "98815": "98815",
    "98816": "98816",
    "98817": "98817",
    "98818": "98818",
    "98819": "98819",
    "98820": "98820",
    "98821": "98821",
    "98822": "98822",
    "98823": "98823",
    "98824": "98824",
    "98825": "98825",
    "98826": "98826",
    "98827": "98827",
    "98828": "98828",
    "98829": "98829",
    "98830": "98830",
    "98831": "98831",
    "98832": "98832",
    "98833": "98833",
}


@cache_projection.memoize(tag="city_projection")
def get_city(
    x: str,
    starting_dates: list,
    projection_date: str,
    log_entries: bool = True,
) -> str:
    """
    Try to get a city's valid official code at projection_date.

    Parameters
    ----------
    x : str
        Obsolete INSEE code (5 digits).
    starting_dates : list
        List of starting dates to query a projection from. Each date should be
        in a "YYYY-MM-DD" format.
    projection_date : str
        Date to project the obsolete code into. Should be in the "YYYY-MM-DD"
        format.
    log_entries : bool, optional
        If True, will display log error if no projection has been found. The
        default is True.

    Returns
    -------
    code
        Valid insee code (5 digits)

    Example
    -------
    >>> get_city(
        "59298",
        starting_dates=[
            "1943-01-01",
            "1960-01-01",
            "1980-01-01",
            "2000-01-01",
            "2010-01-01",
        ],
        projection_date="2024-01-01"
        )

    """
    try:
        return ultra_marine_territories_vintage(x, projection_date)
    except KeyError:
        pass

    starting_dates = sorted(starting_dates)

    # Note: do not parallelize this, starting_dates' order has importance
    for date_init in starting_dates:
        df = get_area_projection(
            code=x,
            area="commune",
            date=date_init,
            dateProjection=projection_date,
            silent=True,
        )
        if not df.empty:
            break
    try:
        return df.at[0, "code"]
    except (ValueError, AttributeError, KeyError):
        if log_entries:
            logger.error("No projection found for city %s", x)
        return None


def _get_cities_year_full(
    year: int, look_for: set = None, threads: int = THREADS
) -> pd.DataFrame:
    """
    Download desired vintage of french official geographic code for cities
    and municipal districts from INSEE API; the obtained DataFrame contains
    two columns : the actual code of the territory and it's parent (which
    should be the same for an actual city, or the parent city for a municipal
    district).

    Parameters
    ----------
    year : int
        Desired vintage
    look_for : set, optional
        List of codes we are trying to project in the desired vintage.
        The default is None (will try to reach every available code).
    threads : int, optional
        Number of threads to use. Default is 10.

    Returns
    -------
    cities : pd.DataFrame

            CODE  NEW_CODE
    0      01001     01001
    1      01002     01002
    2      01004     01004
    3      01005     01005
    4      01006     01006
         ...       ...
    34985  75116     75056
    34986  75117     75056
    34987  75118     75056
    34988  75119     75056
    34989  75120     75056

    """
    cities = _get_cities_year(year, threads=threads)
    data = [
        cities.assign(PARENT=cities["CODE"]),
        _get_subareas_year(
            "arrondissementsMunicipaux", year, look_for, threads=threads
        ),
        _get_subareas_year(
            "communesAssociees", year, look_for, threads=threads
        ),
        _get_subareas_year(
            "communesDeleguees", year, look_for, threads=threads
        ),
    ]
    cities = pd.concat(data, ignore_index=True)
    ix = cities[cities.CODE.isin(look_for)].index
    cities = (
        cities.loc[ix]
        .drop_duplicates(keep="first")
        .reset_index(drop=True)
        .rename({"PARENT": "NEW_CODE"}, axis=1)
    ).copy()
    return cities


def _get_cities_year(year: int, threads: int = THREADS) -> pd.DataFrame:
    """
    Download desired vintage of french official geographic code for cities
    from INSEE API; municipal districts are excluded by this API.

    Parameters
    ----------
    year : int
        Desired vintage
    threads : int, optional
        Number of threads to use. Default is 10.

    Returns
    -------
    cog : pd.DataFrame

        CODE
    0  01001
    1  01002
    2  01004
    3  01005
    4  01006

    """
    cog = get_cities_and_ultramarines(date=f"{year}-01-01", threads=threads)
    try:
        cog = cog.drop("DATE_DELETION", axis=1)
    except KeyError:
        pass
    cog = cog.drop(
        [
            "URI",
            "AREA_TYPE",
            "DETERMINER_TYPE",
            "TITLE",
            "TITLE_SHORT",
            "DATE_CREATION",
        ],
        axis=1,
    )
    return cog


def _get_parents_from_serie(
    type_: str, codes: list, year: int, threads: int = THREADS
) -> pd.DataFrame:
    """
    Get territories' parents codes using INSEE API. The output will be a
    DataFrame containing two columns (one for the actual territory's code, the
    other containing it's parent's code)

    Parameters
    ----------
    type_ : str
        case sensitive, area type, any of ('arrondissement',
        'arrondissementMunicipal', 'circonscriptionTerritoriale', 'commune',
        'communeAssociee', 'communeDeleguee', 'departement',
        'district')
    codes : list
        any iterable of territories' official codes of type type_
    year : int
        Desired vintage
    threads : int, optional
        Number of threads to use. Default is 10.

    Returns
    -------
    parents : pd.DataFrame
           CODE PARENT
       0  13201  13055
       1  13202  13055
       2  13203  13055
       3  13204  13055
       4  13205  13055

    """
    parents = []

    def func(x):
        ret = get_ascending_area(
            code=x,
            area=type_,
            date=f"{year}-01-01",
            type="commune",
            silent=True,
        )
        return {"CODE": x, "PARENT": ret.loc[0, "code"]}

    desc = "Get parent from insee"
    with ThreadPool(threads) as pool:
        # note: there's a rate limiter built-in pynsee, so this is safe
        future = pool.map(func, codes)
        results = future.result()
        parents = list(tqdm(results, total=len(codes), desc=desc, leave=False))

    parents = pd.DataFrame(parents)
    return parents


def _get_subareas_year(
    type_: str,
    year: int,
    look_for: set = None,
    threads: int = THREADS,
) -> pd.DataFrame:
    """
    Download desired vintage of french official geographic code for "subcities"
    (ie municipal districts, associated cities, delegated cities from INSEE API
    and create a link-table allowing to retrieve the parent city's code)

    Parameters
    ----------
    type_ : str
        Type of "subcity", among "arrondissementsMunicipaux",
        'communesAssociees', 'communesDeleguees'
    year : int
        Desired vintage
    look_for : set, optional
        List of codes we are trying to project in the desired vintage.
        The default is None (will try to reach every available code).
    threads : int, optional
        Number of threads to use. Default is 10.

    Returns
    -------
    subareas : pd.DataFrame

        CODE PARENT
    0  13201  13055
    1  13202  13055
    2  13203  13055
    3  13204  13055
    4  13205  13055

    """
    subareas = get_area_list(area=type_, date=f"{year}-01-01", silent=True)
    try:
        subareas = subareas.drop("DATE_DELETION", axis=1)
    except KeyError:
        pass
    drop = [
        "URI",
        "AREA_TYPE",
        "DETERMINER_TYPE",
        "TITLE",
        "DATE_CREATION",
        "TITLE_SHORT",
    ]
    subareas = subareas.drop(drop, axis=1)

    if look_for:
        subareas = subareas[subareas.CODE.isin(look_for)]
    if subareas.empty:
        return pd.DataFrame()

    single_area = {
        "arrondissementsMunicipaux": "arrondissementMunicipal",
        "communesAssociees": "communeAssociee",
        "communesDeleguees": "communeDeleguee",
    }
    type_ = single_area[type_]
    parents = _get_parents_from_serie(
        type_, subareas.CODE.unique(), year, threads=threads
    )
    subareas = subareas.merge(parents, on="CODE", how="left")

    return subareas


def ultra_marine_territories_vintage(code: str, projection_date: str) -> str:
    """
    Make do for INSEE's API lack of coverage of ultramarine collectivities'
    cities vintage projection.

    https://www.insee.fr/fr/information/7929495

    Parameters
    ----------
    code : str
        Cities' initial code to project.
    projection_date : str
        Date to project the obsolete code into. Should be in the "YYYY-MM-DD"
        format.

    Raises
    ------
    KeyError
        If code is not a city code from an ultramarine collectivity.

    Returns
    -------
    str
        Projected code.

    """

    # Codes of cities/districts/circonscriptions unchanging through time:
    try:
        return FIXED_ULTRAMARINE_CODES[code]
    except KeyError:
        pass
    projection_date = datetime.strptime(projection_date, "%Y-%m-%d").date()

    if code in ("97123", "97701"):
        # Saint-Barthélemy
        if projection_date >= date(2008, 1, 1):
            ret = "97701"
        else:
            ret = "97123"

    if code in ("97127" "97801"):
        # Saint-Martin
        if projection_date >= date(2008, 1, 1):
            ret = "97801"
        else:
            ret = "97127"

    if code in ("98799" "98901"):
        # La Passion-Clipperton
        if projection_date >= date(2008, 1, 1):
            ret = "98901"
        else:
            ret = "98799"

    try:
        return ret
    except (UnboundLocalError, NameError) as exc:
        raise KeyError("Not a city from ultramarine collectivities") from exc


@silence_sirene_logs
def set_vintage(
    df: pd.DataFrame, year: int, field: str, threads: int = THREADS
) -> pd.DataFrame:
    """
    Project (approximatively) the cities codes of a dataframe into a desired
    vintage.

    Note that this may **NOT** work for cities which used to whole, then
    merged to another and finally reset as a whole city;
    the algorithm has 50% chances of setting wrong results for any dataset of
    an initial vintage set during this transition period (this should be rare
    enough).

    In case of failure, the projected city code will be set to None.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing city codes
    year : int
        Year to project the dataframe's city codes into
    field : str
        Field (column) of dataframe containing the city code
    threads : int, optional
        Number of threads to use. Default is 10.

    Returns
    -------
    pd.DataFrame
        Projected DataFrame

    Example
    -------
    >>> import pandas as pd
    >>> from french_cities import set_vintage

    >>> df = pd.DataFrame(
        [
            ["07180", "Fusion"],
            ["02077", "Commune déléguée"],
            ["02564", "Commune nouvelle"],
            ["75101", "Arrondissement municipal"],
            ["59298", "Commune associée"],
            ["99999", "Code erroné"],
            ["14472", "Oudon"],
        ],
        columns=["A", "Test"],
        index=["A", "B", "C", "D", 1, 2, 3],
    )
    >>> df = set_vintage(df, 2023, field="A")

    """

    init_pynsee()

    renamed = False
    if field in {"CODE, NEW_CODE"}:
        renamed = True
        df = df.rename({field: f"temp_{field}"}, axis=1)
        field = f"temp_{field}"

    uniques = df[[field]].drop_duplicates(keep="first").dropna()

    if uniques.empty:
        return df

    cities = _get_cities_year_full(year, set(uniques[field]), threads=threads)

    # Uptodate cities (cities, municipal districts, delegated cities, ...)
    uniques = uniques.merge(cities, left_on=field, right_on="CODE", how="left")
    uniques = uniques.rename({"NEW_CODE": "PROJECTED"}, axis=1)

    # Obsolete cities : look for existing projections from old starting dates,
    # using INSEE API
    starting_dates = [
        "1943-01-01",
        "1960-01-01",
        "1980-01-01",
        "2000-01-01",
        "2010-01-01",
    ]

    partial_get_city = partial(
        get_city,
        starting_dates=starting_dates,
        projection_date=f"{year}-01-01",
        log_entries=False,
    )

    def filter_no_data(record):
        return not record.msg.startswith(
            "No data found for projection of area"
        )

    # Note: deactivate pynsee log to substitute by a more accurate
    pynsee_log = logging.getLogger("pynsee.localdata.get_area_projection")
    pynsee_log.addFilter(filter_no_data)

    ix = uniques[uniques.PROJECTED.isnull()].index
    tqdm.pandas(desc="Looking for projections from past", leave=False)

    desc = "Looking for projections from past"
    with ThreadPool(threads) as pool:
        # note: there's a rate limiter built-in pynsee, so this is safe
        future = pool.map(partial_get_city, uniques.loc[ix, field].tolist())
        results = future.result()
        projected = list(tqdm(results, total=len(ix), desc=desc, leave=False))
        uniques.loc[ix, "PROJECTED"] = projected

    pynsee_log.removeFilter(filter_no_data)

    ix = uniques[uniques.PROJECTED.isnull()].index

    def log_after_tqdm(x):
        logger.error("No projection found for city %s", x)

    uniques.loc[ix, field].apply(log_after_tqdm)

    uniques = dict(uniques[[field, "PROJECTED"]].values)

    df.loc[:, field] = df.loc[:, field].map(uniques)

    if renamed:
        df = df.rename({field: field.lstrip("temp_")}, axis=1)

    return df
