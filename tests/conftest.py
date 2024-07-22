# -*- coding: utf-8 -*-
"""
Created on Mon Jul 22 22:12:42 2024

Used to remove all cache during tests
"""


def pytest_sessionstart(session):
    from french_cities.utils import clear_all_cache

    clear_all_cache()


def pytest_sessionfinish(session, exitstatus):
    from french_cities.utils import clear_all_cache

    clear_all_cache()
