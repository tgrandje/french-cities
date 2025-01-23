# -*- coding: utf-8 -*-

import logging
import os

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    after_log,
)
import tenacity._utils

from pynsee.utils import _request_insee
import pynsee.localdata
from pyrate_limiter import SQLiteBucket
import requests
from requests.packages.urllib3.util.retry import Retry
from requests_ratelimiter import LimiterAdapter

import pynsee.utils

from french_cities import DIR_CACHE

logger = logging.getLogger(__name__)


def traceback_after_retries(retry_state):
    logger.error(
        f"An error happened in {retry_state.fn} with the following arguments "
        f"args={retry_state.args}"
    )
    return retry_state.outcome


class CustomLimiterSession(requests.Session):
    """
    Session class used to patch pynsee's request with a rate-limiter and custom
    retry/timeout, awaiting next release
    """

    def __init__(self):

        super().__init__()

        retry = Retry(
            total=7, backoff_factor=1, status_forcelist=[429, 502, 503, 504]
        )
        rate_backend_path = os.path.join(DIR_CACHE, "rate_pynsee.sqlite")

        adapter = LimiterAdapter(
            per_minute=30,
            bucket_class=SQLiteBucket,
            bucket_kwargs={
                "path": rate_backend_path,
                "isolation_level": "EXCLUSIVE",
                "check_same_thread": False,
            },
            max_retries=retry,
        )

        self.mount("https://api.insee.fr", adapter)

    @retry(
        reraise=True,
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        after=after_log(logger, logging.WARNING),
        retry_error_callback=traceback_after_retries,
    )
    def request(self, method, url, timeout=(10, 15), **kwargs):
        logger.info(url)
        response = super().request(method, url, timeout=timeout, **kwargs)
        return response


def _insee_ratelimit():
    """
    Patch pynsee's session to avoid reaching the 30 queries/min threshold, due
    to be fixed in next pynsee's release

    Returns
    -------
    None

    """

    session = CustomLimiterSession()

    def patched_session():
        return session

    _request_insee._get_requests_session = patched_session


def after_log(
    logger: "logging.Logger",
    log_level: int,
    sec_format: str = "%0.3f",
):
    """After call strategy that logs to some logger the finished attempt."""

    def log_it(retry_state):
        if retry_state.fn is None:
            # NOTE(sileht): can't really happen, but we must please mypy
            fn_name = "<unknown>"
        else:
            fn_name = tenacity._utils.get_callback_name(retry_state.fn)

        if retry_state.attempt_number <= 1:
            log_level_inner = logging.INFO
        else:
            log_level_inner = log_level

        logger.log(
            log_level_inner,
            f"Finished call to '{fn_name}' with args={retry_state.args}"
            f"after {sec_format % retry_state.seconds_since_start}(s), "
            "this was the "
            f"{tenacity._utils.to_ordinal(retry_state.attempt_number)} "
            "time calling it.",
        )

    return log_it


KWARGS_RETRY = {
    "reraise": True,
    "stop": stop_after_attempt(5),
    "wait": wait_exponential(multiplier=1, min=4, max=10),
    "after": after_log(logger, logging.WARNING),
}

# =============================================================================
# Patch pynsee's inner functions to force retries
# =============================================================================


@retry(**KWARGS_RETRY)
def get_area_list(*args, **kwargs):
    ret = pynsee.localdata.get_area_list(*args, **kwargs)
    return ret


@retry(**KWARGS_RETRY)
def get_descending_area(*args, **kwargs):
    ret = pynsee.localdata.get_descending_area(*args, **kwargs)
    return ret


@retry(**KWARGS_RETRY)
def get_area_projection(*args, **kwargs):
    ret = pynsee.localdata.get_area_projection(*args, **kwargs)
    return ret


@retry(**KWARGS_RETRY)
def get_ascending_area(*args, **kwargs):
    ret = pynsee.localdata.get_ascending_area(*args, **kwargs)
    return ret


# if __name__ == "__main__":
#     r = get_descending_area("collectiviteDOutreMer", "985", "2025-01-01")
