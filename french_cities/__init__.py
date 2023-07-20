# -*- coding: utf-8 -*-

from dotenv import load_dotenv

# https://www.insee.fr/fr/information/6800675#communes_1943
LAST_INSEE_HISTO_CITIES = "https://www.insee.fr/fr/statistiques/fichier/6800675/v_commune_depuis_1943.csv"

from french_cities.city_finder import find_city
from french_cities.departement_finder import find_departements
from french_cities.vintage import set_vintage

load_dotenv()

__version__ = "0.1.0a3"


__all__ = [
    "find_city",
    "find_departements",
    "set_vintage",
]
