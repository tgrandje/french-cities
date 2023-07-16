# -*- coding: utf-8 -*-
"""
Created on Tue Jul 11 09:20:26 2023
"""
from unittest import TestCase
import pandas as pd
import numpy as np

from french_cities.city_finder import find_city


class test_find_city(TestCase):
    def setUp(self):
        self.input = pd.DataFrame(
            [
                {
                    "x": 2.294694,
                    "y": 48.858093,
                    "location": "Tour Eiffel",
                    "dep": "75",
                    "city": "Paris",
                    "address": "5 Avenue Anatole France",
                    "postcode": "75007",
                    "target": "75056",
                },
                {
                    "x": 8.738962,
                    "y": 41.919216,
                    "location": "mairie",
                    "dep": "2A",
                    "city": "Ajaccio",
                    "address": "Antoine Sérafini",
                    "postcode": "20000",
                    "target": "2A004",
                },
                {
                    "x": -52.334990,
                    "y": 4.938194,
                    "location": "mairie",
                    "dep": "973",
                    "city": "Cayenne",
                    "address": "1 rue de Rémire",
                    "postcode": "97300",
                    "target": "97302",
                },
                {
                    "x": np.nan,
                    "y": np.nan,
                    "location": "Erreur code postal Lille/Lyon",
                    "dep": "59",
                    "city": "Lille",
                    "address": "1 rue Faidherbe",
                    "postcode": "69000",
                    "target": "59350",
                },
                {
                    "x": np.nan,
                    "y": np.nan,
                    "location": "Erreur adresse Lille/Lambersart",
                    "dep": "59",
                    "city": "Lille",
                    "address": "199 avenue Pasteur",
                    "postcode": "59000",
                    "target": "59328",
                },
                {
                    "x": np.nan,
                    "y": np.nan,
                    "location": "Commune fusionnée",
                    "dep": "01",
                    "city": "Béon",
                    "address": np.nan,
                    "postcode": "01350",
                    "target": "01138",
                },
                {
                    "x": np.nan,
                    "y": np.nan,
                    "location": "Commune homonyme",
                    "dep": "60",
                    "city": "Saint-Sauveur",
                    "address": np.nan,
                    "postcode": np.nan,
                    "target": "60597",
                },
                {
                    "x": np.nan,
                    "y": np.nan,
                    "location": "Commune formatté comme Legifrance",
                    "dep": "02",
                    "city": "Sourd (Le)",
                    "address": np.nan,
                    "postcode": np.nan,
                    "target": "02731",
                },
            ],
        )
        self.output = find_city(self.input, epsg=4326)
        print(self.output)

    def test_class(self):
        assert isinstance(self.output, pd.DataFrame)

    def test_shape(self):
        assert (
            np.array(self.output.shape)
            == (np.array(self.input.shape) + np.array([0, 1]))
        ).all()

    def test_columns(self):
        assert set(self.output.columns) == (set(self.input.columns) | {"insee_com"})

    def test_indexes(self):
        assert (self.input.index == self.output.index).all()

    def test_content(self):
        assert (self.output["insee_com"] == self.output["target"]).all()
