# -*- coding: utf-8 -*-
"""
Created on Fri Jul  7 09:17:12 2023
"""
import pandas as pd
from functools import partial
from tqdm import tqdm
import logging

from french_cities.utils import init_pynsee
from pynsee.localdata import get_area_list
from pynsee.localdata import get_ascending_area
from pynsee.localdata import get_area_projection

logger = logging.getLogger(__name__)


def _get_cities_year_full(year: int, look_for: set = None) -> pd.DataFrame:
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
    cities = _get_cities_year(year)
    data = [
        cities.assign(PARENT=cities["CODE"]),
        _get_subareas_year("arrondissementsMunicipaux", year, look_for),
        _get_subareas_year("communesAssociees", year, look_for),
        _get_subareas_year("communesDeleguees", year, look_for),
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


def _get_cities_year(year: int) -> pd.DataFrame:
    """
    Download desired vintage of french official geographic code for cities
    from INSEE API; municipal districts are excluded by this API.

    Parameters
    ----------
    year : int
        Desired vintage

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
    date = f"{year}-01-01"
    cog = get_area_list(area="communes", date=date)
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
    type_: str, codes: list, year: int
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
    date = f"{year}-01-01"
    parents = []
    func = partial(get_ascending_area, area=type_, date=date, type="commune")
    for code in tqdm(codes, desc="get parent from insee", leave=False):
        parents.append(
            {"CODE": code, "PARENT": func(code=code).loc[0, "code"]}
        )

    parents = pd.DataFrame(parents)
    return parents


def _get_subareas_year(
    type_: str, year: int, look_for: set = None
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
    date = f"{year}-01-01"
    subareas = get_area_list(area=type_, date=date)
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
    parents = _get_parents_from_serie(type_, subareas.CODE.unique(), year)
    subareas = subareas.merge(parents, on="CODE", how="left")

    return subareas


def set_vintage(df: pd.DataFrame, year: int, field: str) -> pd.DataFrame:
    """
    Project (approximatively) the cities codes of a dataframe into a desired
    vintage.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing city codes
    year : int
        Year to project the dataframe's city codes into
    field : str
        Field (column) of dataframe containing the city code

    Returns
    -------
    pd.DataFrame
        Projected DataFrame

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

    cities = _get_cities_year_full(year, set(uniques[field]))

    # Uptodate cities (cities, municipal districts, delegated cities, ...)
    uniques = uniques.merge(
        cities, left_on=field, right_on="CODE", how="left"
    )
    uniques = uniques.rename({"NEW_CODE": "PROJECTED"}, axis=1)

    # Obsolete cities : merge, etc. : look for projection starting from an old
    # date, using INSEE API
    date = f"{year}-01-01"
    starting_dates = [
        "1943-01-01",
        "1960-01-01",
        "1980-01-01",
        "2000-01-01",
        "2010-01-01",
    ]

    def get_city(x):
        for date_init in starting_dates:
            # Hack to deactivate standard error log entries by pynsee which are
            # concieved with a valid date in mind.
            previous_level = logging.root.manager.disable
            logging.disable(logging.ERROR)
            df = get_area_projection(
                code=x, area="commune", date=date_init, dateProjection=date
            )
            try:
                df = df.drop("DATE_DELETION", axis=1)
            except (KeyError, AttributeError):
                pass
            logging.disable(previous_level)

            if df is not None:
                break
        try:
            return df.at[0, "code"]
        except Exception:
            logger.error(f"No projection found for city {x}")
            return None

    ix = uniques[uniques.PROJECTED.isnull()].index
    uniques.loc[ix, "PROJECTED"] = uniques.loc[ix, field].apply(get_city)

    uniques = dict(uniques[[field, "PROJECTED"]].values)

    df.loc[:, field] = df.loc[:, field].map(uniques)

    if renamed:
        df = df.rename({field: field.lstrip("temp_")}, axis=1)

    return df
