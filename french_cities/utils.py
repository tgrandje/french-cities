# -*- coding: utf-8 -*-

from functools import lru_cache
import logging
import os

import diskcache

import pynsee.utils
from pynsee.utils import init_conn
from pynsee.utils._clean_insee_folder import _clean_insee_folder

from french_cities import DIR_CACHE


def silence_sirene_logs(func):
    """
    decorator deactivating critical/error/warning log entries from pynsee on
    missing SIRENE credentials:  this is intended behaviour in french-cities
    context
    """

    def filter_no_credential_or_no_results(record):
        return (
            # no credentials:
            not record.msg.startswith(
                "INSEE API credentials have not been found"
            )
            and not record.msg.startswith(
                "Invalid credentials, the following APIs returned error codes"
            )
            and not record.msg.startswith(
                "Remember to subscribe to SIRENE API"
            )
            # no results, but switch to a more accurate log entry in
            # french-cities context:
            and record.msg != "No data found !"
            and not not record.msg.startswith(
                "No data found for projection of area"
            )
        )

    def wrapper(*args, **kwargs):
        # Note: deactivate pynsee log to substitute by a more accurate
        pynsee_logs = (
            "pynsee.utils._get_credentials",
            "pynsee.utils.requests_session",
            "pynsee.utils.init_connection",
            "pynsee.localdata.get_descending_area",
        )
        for log in pynsee_logs:
            pynsee_log = logging.getLogger(log)
            pynsee_log.propagate = False
            pynsee_log.addFilter(filter_no_credential_or_no_results)
        try:
            return func(*args, **kwargs)
        except Exception:
            raise
        finally:
            for log in pynsee_logs:
                pynsee_log = logging.getLogger(log)
                pynsee_log.propagate = True
                pynsee_log.removeFilter(filter_no_credential_or_no_results)

    return wrapper


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


@silence_sirene_logs
@lru_cache(maxsize=None)
def init_pynsee():
    """
    Initiate an INSEE API connection with proxies.
    """
    keys = ["http_proxy", "https_proxy"]
    kwargs = {x: os.environ[x] for x in keys if x in os.environ}
    kwargs["sirene_key"] = None

    init_conn(**kwargs)
