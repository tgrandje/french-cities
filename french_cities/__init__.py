# -*- coding: utf-8 -*-


from dotenv import load_dotenv
from importlib_metadata import version

from .config import DIR_CACHE
from .city_finder import find_city
from .departement_finder import (
    find_departements,
    find_departements_from_names,
)
from .vintage import set_vintage

load_dotenv(override=True)

__version__ = version(__package__)


__all__ = [
    "find_city",
    "find_departements",
    "find_departements_from_names",
    "set_vintage",
]
