# -*- coding: utf-8 -*-


import pandas as pd

from french_cities.ultramarine_pseudo_cog import _get_ultramarines_cities


def test_ultramarine_pseudo_cog():
    df = _get_ultramarines_cities(update=True)
    assert isinstance(df, pd.DataFrame)


def assert_pseudo_deps_ultramarine():
    df = _get_ultramarines_cities(date="2024-01-01", update=True)
    pseudo_deps = df.CODE.str[:3].drop_duplicates()
    assert len(pseudo_deps) == 7
