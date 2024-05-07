# -*- coding: utf-8 -*-

from dotenv import load_dotenv
from importlib_metadata import version

from french_cities.city_finder import find_city
from french_cities.departement_finder import (
    find_departements,
    find_departements_from_names,
    )
from french_cities.vintage import set_vintage

load_dotenv(override=True)

__version__ = version(__package__)


__all__ = [
    "find_city",
    "find_departements",
    "find_departements_from_names",
    "set_vintage",
]
