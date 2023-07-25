# -*- coding: utf-8 -*-

from pynsee.utils import clear_all_cache
from pynsee.utils.init_conn import init_conn
import os
from pathlib import Path


def init_pynsee():
    home = str(Path.home())
    pynsee_credentials_file = os.path.join(home, "pynsee_credentials.csv")
    if not os.path.exists(pynsee_credentials_file):
        clear_all_cache()
        keys = ["insee_key", "insee_secret", "http_proxy", "https_proxy"]
        kwargs = {x: os.environ[x] for x in keys if x in os.environ}
        init_conn(**kwargs)
