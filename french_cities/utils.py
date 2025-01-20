# -*- coding: utf-8 -*-

import os
from pathlib import Path

import diskcache

from french_cities.pynsee_patch import _insee_ratelimit

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
    [
        os.unlink(f.path)
        for f in os.scandir(DIR_CACHE)
        if not f.is_dir()
        # Do NOT reboot the API's rate consumption!
        and not "rate_pynsee" in f.path
    ]

    # Clear pynsee's cache
    pynsee.utils.clear_all_cache()
    _clean_insee_folder()


def init_pynsee():
    """
    Initiate an INSEE API connection with tokens and proxies.
    """
    home = str(Path.home())
    pynsee_credentials_file = os.path.join(home, "pynsee_credentials.csv")
    _insee_ratelimit()
    if not os.path.exists(pynsee_credentials_file):
        clear_all_cache()
        keys = ["insee_key", "insee_secret", "http_proxy", "https_proxy"]
        kwargs = {x: os.environ[x] for x in keys if x in os.environ}

        init_conn(**kwargs)
