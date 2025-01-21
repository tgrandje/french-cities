# -*- coding: utf-8 -*-

from functools import lru_cache
import os

import diskcache

import pynsee.utils
from pynsee.utils.init_conn import init_conn
from pynsee.utils._clean_insee_folder import _clean_insee_folder

from french_cities import DIR_CACHE


def clear_all_cache():
    "Clear french-cities cache first, then pynsee's"

    # Clear diskcache's caches
    for cache_name in (
        "projection",
        "deps",
        "nominatim",
        "ultramarine",
    ):
        with diskcache.Cache(os.path.join(DIR_CACHE, cache_name)) as cache:
            cache.clear()

    # Clear request-cache's cache
    [os.unlink(f.path) for f in os.scandir(DIR_CACHE) if not f.is_dir()]

    # Clear pynsee's cache
    pynsee.utils.clear_all_cache()
    _clean_insee_folder()


@lru_cache(maxsize=None)
def init_pynsee():
    """
    Initiate an INSEE API connection with proxies.
    """
    keys = ["http_proxy", "https_proxy"]
    kwargs = {x: os.environ[x] for x in keys if x in os.environ}
    kwargs["sirene_key"] = None
    init_conn(**kwargs)
