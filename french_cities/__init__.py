# -*- coding: utf-8 -*-

from dotenv import load_dotenv

from french_cities.city_finder import find_city
from french_cities.departement_finder import find_departements
from french_cities.vintage import set_vintage

load_dotenv()

__version__ = "0.1.0a6"


__all__ = [
    "find_city",
    "find_departements",
    "set_vintage",
]
