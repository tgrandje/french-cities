# -*- coding: utf-8 -*-
"""
Created on Sun Jul 21 20:27:29 2024

Gather ultramarine territories as well as formal cities from french department.
This allows to recognized ultramarine territories.
"""

import datetime
import logging
import os

import diskcache
import pandas as pd

from pynsee.localdata import get_area_list, get_descending_area
from requests.exceptions import RequestException
from tqdm import tqdm

from french_cities import DIR_CACHE

logger = logging.getLogger(__name__)


def set_default_date():
    date = datetime.date(datetime.date.today().year, 1, 1)
    date = date.strftime("%Y-%m-%d")
    return date


def _get_ultramarines_cities(
    date: str = None, update: bool = None
) -> pd.DataFrame:
    """
    Retrieve ultramarine cities.

    Retrieve all territories at the (more or less) similar level than cities
    in the ultramarine territories: communes, circonscriptions territoriales
    and districts.

    Parameters
    ----------
    date : str, optional
        date used to analyse the data, format : 'AAAA-MM-JJ'. If date is None,
        by default the current date is used.
    update : bool, optional
        Locally saved data is used by default. Trigger an update with
        update=True.

    Returns
    -------
    cities : pd.DataFrame
        DataFrame of cities and semi-equivalents.

    """

    area = "collectivitesDOutreMer"
    um = get_area_list(
        area,
        date,
        update,
        silent=True,
    )
    if date == "*":
        date = set_default_date()
        warning = (
            f"get_descending_area with {area=} does not support date='*': "
            f"querying for {date=} instead"
        )
        logging.warning(warning)
    if not date:
        date = set_default_date()

    cache_ultramarine = diskcache.Cache(os.path.join(DIR_CACHE, "ultramarine"))
    try:
        if not update:
            cities = cache_ultramarine[date]
            return cities
        pass
    except KeyError:
        pass

    # TODO : parallélisation
    desc = "Get descending area for ultra-marine territories"
    cities = []
    for code in tqdm(um["CODE"], total=len(um), desc=desc, leave=False):
        types = ["Commune", "CirconscriptionTerritoriale", "District"]
        while types:
            try:
                this_territory = get_descending_area(
                    "collectiviteDOutreMer",
                    code,
                    date,
                    update=update,
                    type=types.pop(0),
                    silent=True,
                )
                if this_territory.empty:
                    raise IndexError
            except RequestException:
                continue
            except IndexError:
                continue
            else:
                break
        if this_territory is None or this_territory.empty:
            logger.info("No cities found for ultramarine territory %s", code)
        cities.append(this_territory)

    cities = pd.concat(cities)
    cities = cities.rename(
        {
            "code": "CODE",
            "uri": "URI",
            "type": "AREA_TYPE",
            "dateCreation": "DATE_CREATION",
            "intituleSansArticle": "TITLE_SHORT",
            "typeArticle": "DETERMINER_TYPE",
            "intitule": "TITLE",
        },
        axis=1,
    )

    cache_ultramarine[date] = cities

    return cities


def get_cities_and_ultramarines(
    date: str = None, update: bool = None
) -> pd.DataFrame:
    """
    Retrieve a unified DataFrame of cities (from departements and ultramarine
    territories both).

    Parameters
    ----------
    date : str, optional
        date used to analyse the data, format : 'AAAA-MM-JJ'. If date is None,
        by default the current date is used.
    update : bool, optional
        Locally saved data is used by default. Trigger an update with
        update=True.

    Returns
    -------
    full : pd.DataFrame
        Full DataFrame of cities and equivalents.

    """

    ultramarine = _get_ultramarines_cities(date, update)
    cities = get_area_list("communes", date, update, silent=True)
    full = pd.concat([ultramarine, cities], ignore_index=True)
    return full


def get_departements_and_ultramarines(date=None, update=None):
    """
    Retrieve a unified DataFrame of departments and ultramarine territories
    both.

    Parameters
    ----------
    date : str, optional
        date used to analyse the data, format : 'AAAA-MM-JJ'. If date is None,
        by default the current date is used.
    update : bool, optional
        Locally saved data is used by default. Trigger an update with
        update=True.

    Returns
    -------
    full : pd.DataFrame

    """
    ultramarine = get_area_list(
        "collectivitesDOutreMer", date, update, silent=True
    )
    ultramarine = ultramarine.sort_values(["CODE", "DATE_CREATION"])

    deps = get_area_list("departements", date, update, silent=True)
    deps = deps.drop("chefLieu", axis=1)
    full = pd.concat([ultramarine, deps], ignore_index=True)
    return full


if __name__ == "__main__":
    from french_cities.utils import init_pynsee

    # os.environ["http_proxy"] = ""
    # os.environ["https_proxy"] = ""
    init_pynsee()
    df = _get_ultramarines_cities("2023-01-01", update=True)
    print(df)
