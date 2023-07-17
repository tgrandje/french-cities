# -*- coding: utf-8 -*-

from pynsee.utils import clear_all_cache
from pynsee.utils.init_conn import init_conn
import os


def init_pynsee():
    clear_all_cache()
    keys = ["insee_key", "insee_secret", "http_proxy", "https_proxy"]
    kwargs = {x: os.environ[x] for x in keys if x in os.environ}
    init_conn(**kwargs)
