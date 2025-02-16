# -*- coding: utf-8 -*-
"""
Created on Tue Jul 11 09:20:26 2023
"""
from unittest import TestCase
from unittest.mock import patch
import pandas as pd
import numpy as np
from requests import session

from french_cities.city_finder import find_city

input_df = pd.DataFrame(
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
        # {
        # "x": np.nan,
        # "y": np.nan,
        # "location": "Erreur adresse Lille/Lambersart",
        # "dep": "59",
        # "city": "Lille",
        # "address": "199 avenue Pasteur",
        # "postcode": "59000",
        # "target": "59328",  # Lille
        # },
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
            "city": "St-Sauveur",
            "address": np.nan,
            "postcode": np.nan,
            "target": "60597",
        },
        {
            "x": np.nan,
            "y": np.nan,
            "location": "Commune formatté Legifrance et erreur de code postal",
            "dep": "02",
            "city": "Sourd (Le)",
            "address": np.nan,
            "postcode": "2140",
            "target": "02731",
        },
        {
            "x": np.nan,
            "y": np.nan,
            "location": "Ancienne commune mal formatée",
            "dep": "59",
            "city": "Mardyk",
            "address": np.nan,
            "postcode": np.nan,
            "target": "59183",  # Dunkerque
        },
        {
            "x": np.nan,
            "y": np.nan,
            "location": "Homonyme rue/commune",
            "dep": "59",
            "city": "Bouchain",
            "address": np.nan,
            "postcode": np.nan,
            "target": "59092",
        },
        {
            "x": np.nan,
            "y": np.nan,
            "location": "Homonyme rue/commune",
            "dep": "59",
            "city": "Loos",
            "address": np.nan,
            "postcode": np.nan,
            "target": "59360",
        },
        {
            "x": np.nan,
            "y": np.nan,
            "location": "Homonyme rue/commune",
            "dep": "62",
            "city": "Isbergues",
            "address": np.nan,
            "postcode": np.nan,
            "target": "62473",
        },
        {
            "x": np.nan,
            "y": np.nan,
            "location": "Station de ski",
            "dep": "74",
            "city": "Avoriaz",
            "address": np.nan,
            "postcode": np.nan,
            "target": "74191",
        },
    ],
    index=[10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21],
)


class MockedResponse:
    ok = True
    content = (
        b"dep,city_cleaned,postcode,address,full,result_score,result_city,"
        b"result_citycode\r\n"
        b"74,AVORIAZ,,,74 AVORIAZ,0.35677393939393937,Morzine,74191\r\n"
    )

    def json(self):
        return {
            "type": "FeatureCollection",
            "version": "draft",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [2.474484, 49.767999],
                    },
                    "properties": {
                        "label": "Morisel",
                        "score": 0.16301377622377625,
                        "id": "80571",
                        "type": "municipality",
                        "name": "Morisel",
                        "postcode": "80110",
                        "citycode": "80571",
                        "x": 662115.98,
                        "y": 6963355.46,
                        "population": 486,
                        "city": "Morisel",
                        "context": "80, Somme, Hauts-de-France",
                        "importance": 0.25469,
                        "municipality": "Morisel",
                    },
                }
            ],
            "attribution": "BAN",
            "licence": "ETALAB-2.0",
            "query": "74 AVORIAZ",
            "filters": {"type": "municipality"},
            "limit": 1,
        }


class MockedSession:
    def post(self, *args, **kwargs):
        return MockedResponse()

    def get(self, *args, **kwargs):
        return MockedResponse()


output_df = find_city(
    input_df.copy(),
    epsg=4326,
    use_nominatim_backend=True,
    session=MockedSession(),
)

output_df2 = find_city(
    pd.DataFrame(
        [
            {
                "x": 2.294694,
                "y": 48.858093,
                "location": "Tour Eiffel",
                "city": "Paris",
                "address": "5 Avenue Anatole France",
                "postcode": "75007",
                "target": "75056",
            }
        ]
    ),
    year="2023",
    epsg=4326,
    use_nominatim_backend=True,
    dep=False,
)


class test_find_city(TestCase):

    def test_class(self):
        assert isinstance(output_df, pd.DataFrame)

    def test_shape(self):
        assert (
            np.array(output_df.shape)
            == (np.array(input_df.shape) + np.array([0, 1]))
        ).all()

    def test_columns(self):
        assert set(output_df.columns) == (
            set(input_df.columns) | {"insee_com"}
        )

    def test_indexes(self):
        assert (input_df.index == output_df.index).all()

    def test_content(self):
        assert (output_df["insee_com"] == output_df["target"]).all()

    def test_live(self):
        assert (output_df2["insee_com"] == output_df2["target"]).all()

    def test_raises_wrong_vintage_input(self):

        df = pd.DataFrame(
            [
                {
                    "x": 2.294694,
                    "y": 48.858093,
                    "location": "Tour Eiffel",
                    "city": "Paris",
                    "address": "5 Avenue Anatole France",
                    "postcode": "75007",
                    "target": "75056",
                }
            ]
        )

        self.assertRaises(ValueError, find_city, df=df, year="2023-01-01")

    def test_raises_not_enough_fields(self):
        """
        check that missing EPSG results to x/y not being used and that not
        enough data results to a ValueError
        """

        df = pd.DataFrame(
            [
                {
                    "location": "Tour Eiffel",
                    "city": "Paris",
                    "x": 2.294694,
                    "y": 48.858093,
                }
            ]
        )

        self.assertRaises(ValueError, find_city, df=df, epsg=None)
