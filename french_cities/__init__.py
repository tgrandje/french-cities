# -*- coding: utf-8 -*-

from dotenv import load_dotenv
from pynsee.utils import clear_all_cache
from pynsee.utils.init_conn import init_conn
import os

from french_cities.city_finder import find_city
from french_cities.departement_finder import process_departements
from french_cities.vintage import set_vintage

load_dotenv()

__version__ = "0.1.0"


def init_pynsee():
    clear_all_cache()
    keys = ["insee_key", "insee_secret", "http_proxy", "https_proxy"]
    kwargs = {x: os.environ[x] for x in keys if x in os.environ}
    init_conn(**kwargs)


init_pynsee()
