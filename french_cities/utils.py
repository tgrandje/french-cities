# -*- coding: utf-8 -*-

from contextlib import contextmanager
import diskcache
import os
from pathlib import Path

import pynsee.utils
from pynsee.utils.init_conn import init_conn
import requests_cache

from french_cities import DIR_CACHE


def clear_all_cache():
    "Clear french-cities cache first, then pynsee's"

    # Clear diskcache's caches
    for cache_name in "projection", "deps", "nominatim", "ultramarine":
        with diskcache.Cache(os.path.join(DIR_CACHE, cache_name)) as cache:
            cache.clear()

    # Clear request-cache's cache
    [os.unlink(f.path) for f in os.scandir(DIR_CACHE) if not f.is_dir()]

    # Clear pynsee's cache
    pynsee.utils.clear_all_cache()


def init_pynsee():
    """
    Initiate an INSEE API connection with tokens and proxies.
    """
    home = str(Path.home())
    pynsee_credentials_file = os.path.join(home, "pynsee_credentials.csv")
    if not os.path.exists(pynsee_credentials_file):
        clear_all_cache()
        keys = ["insee_key", "insee_secret", "http_proxy", "https_proxy"]
        kwargs = {x: os.environ[x] for x in keys if x in os.environ}
        init_conn(**kwargs)


@contextmanager
def patch_the_patch():
    """
    Patches the multipart form boundary and prevent underscore (crashing the
    BAN webserver)
    """
    init_val = requests_cache._utils.FORM_BOUNDARY
    requests_cache._utils.FORM_BOUNDARY = "requests-cache-form-boundary"
    yield
    requests_cache._utils.FORM_BOUNDARY = init_val
