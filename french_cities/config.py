# -*- coding: utf-8 -*-
"""
Created on Wed Jul 17 13:43:12 2024

Create a cache directory to store all data for french-cities.
On windows, the directory should be in %localAppData%/french-cities.
"""

import platformdirs

APP_NAME = "french-cities"
DIR_CACHE = platformdirs.user_cache_dir(APP_NAME, ensure_exists=True)
