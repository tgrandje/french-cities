# -*- coding: utf-8 -*-
"""
Created on Tue Jul 11 09:20:26 2023
"""
from unittest import TestCase
import pandas as pd
import numpy as np

from french_cities.city_finder import _find_from_geoloc


class test_find_from_geoloc(TestCase):
    def setUp(self):
        self.input = pd.DataFrame(
            [
                {"x": 2.294694, "y": 48.858093, "location": "Eiffel Tower"},
                {"x": 8.73462, "y": 41.92723, "location": "Ajaccio"},
                {"x": -52.326000, "y": 4.937200, "location": "Cayenne"},
            ]
        )
        self.output = _find_from_geoloc(4326, self.input)

    def test_class(self):
        assert isinstance(self.output, pd.DataFrame)

    def test_shape(self):
        assert (
            np.array(self.output.shape)
            == (np.array(self.input.shape) + np.array([1, 0]))
        ).all()

    def test_columns(self):
        assert set(self.input.columns) == {"x", "y", "location", "insee_com"}

    def test_indexes(self):
        assert (self.input.index == self.output.index).all()

    def test_content(self):
        assert set(self.input["insee_com"]) == ["75056", "2A004", "97302"]
