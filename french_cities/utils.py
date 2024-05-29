# -*- coding: utf-8 -*-

from pynsee.utils import clear_all_cache
from pynsee.utils.init_conn import init_conn
import os
from pathlib import Path
from contextlib import contextmanager
import requests_cache


def init_pynsee():
    home = str(Path.home())
    pynsee_credentials_file = os.path.join(home, "pynsee_credentials.csv")
    if not os.path.exists(pynsee_credentials_file):
        clear_all_cache()
        keys = ["insee_key", "insee_secret", "http_proxy", "https_proxy"]
        kwargs = {x: os.environ[x] for x in keys if x in os.environ}
        init_conn(**kwargs)


@contextmanager
def patch_the_patch():
    init_val = requests_cache._utils.FORM_BOUNDARY
    requests_cache._utils.FORM_BOUNDARY = "requests-cache-form-boundary"
    yield
    requests_cache._utils.FORM_BOUNDARY = init_val
