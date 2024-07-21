# -*- coding: utf-8 -*-
"""
Created on Wed Jul 17 13:43:12 2024
"""

import platformdirs

appname = "french-cities"
DIR_CACHE = platformdirs.user_cache_dir(appname, ensure_exists=True)
