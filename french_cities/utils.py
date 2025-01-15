# -*- coding: utf-8 -*-

import diskcache
import os
from pathlib import Path

from pynsee.utils import _request_insee
from pyrate_limiter import SQLiteBucket
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from requests_ratelimiter import LimiterSession

import pynsee.utils
from pynsee.utils.init_conn import init_conn

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
        if not f.is_dir() and not "rate_pynsee" in f.path
    ]

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

        _insee_ratelimit()

        init_conn(**kwargs)


def _insee_ratelimit():
    """
    Patch pynsee's session to avoid reaching the 30 queries/min threshold, due
    to be fixed in next pynsee's release

    Returns
    -------
    None

    """

    session = requests.Session()

    adapter = LimiterSession(
        per_minute=30,
        bucket_class=SQLiteBucket,
        bucket_kwargs={
            "path": os.path.join(DIR_CACHE, "rate_pynsee.sqlite"),
            "isolation_level": "EXCLUSIVE",
            "check_same_thread": False,
        },
    )
    import logging

    logging.error(os.path.join(DIR_CACHE, "rate_pynsee.sqlite"))
    session.mount("https://api.insee.fr", adapter)
    retry = Retry(total=7, connect=3, backoff_factor=1)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    def patched_session():
        return session

    _request_insee._get_requests_session = patched_session
