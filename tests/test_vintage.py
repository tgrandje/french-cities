# -*- coding: utf-8 -*-
"""
Created on Mon Jul 10 08:45:15 2023
"""

from unittest import TestCase
import pandas as pd

from french_cities.vintage import (
    _get_cities_year_full,
    _get_cities_year,
    # _get_parents_from_serie,  # -> testé via _get_subareas_year
    _get_subareas_year,
    set_vintage,
)


# %% _get_cities_year_full
class test_get_cities_year_full(TestCase):
    def setUp(self):
        self.cities = _get_cities_year_full(2023, look_for=["02077", "02564"])

    def test_class(self):
        assert isinstance(self.cities, pd.DataFrame)

    def test_shape(self):
        assert self.cities.shape == (2, 2)

    def test_columns(self):
        assert self.cities.columns.tolist() == ["CODE", "NEW_CODE"]

    def test_content(self):
        assert dict(self.cities.values) == {
            "02564": "02564",
            "02077": "02564",
        }


# %% _get_cities_year
class test_get_cities_year(TestCase):
    def setUp(self):
        self.cities = _get_cities_year(2023)

    def test_class(self):
        assert isinstance(self.cities, pd.DataFrame)

    def test_shape(self):
        assert self.cities.shape == (35038, 1)

    def test_columns(self):
        assert self.cities.columns == ["CODE"]

    def test_content(self):
        assert "01001" in set(self.cities["CODE"])


# %% _get_subareas_year
arr = _get_subareas_year("arrondissementsMunicipaux", 2023)
arr_selected = _get_subareas_year(
    "arrondissementsMunicipaux", 2023, look_for=["75101"]
)
delegated = _get_subareas_year("communesDeleguees", 2023, look_for={"01039"})
associated = _get_subareas_year("communesAssociees", 2023, look_for={"59298"})
empty = _get_subareas_year("communesAssociees", 2023, look_for={"59350"})


class test_get_subareas_year(TestCase):
    def test_class(self):
        assert isinstance(arr, pd.DataFrame)
        assert isinstance(delegated, pd.DataFrame)
        assert isinstance(associated, pd.DataFrame)
        assert isinstance(arr_selected, pd.DataFrame)
        assert isinstance(empty, pd.DataFrame)

    def test_error(self):
        assert empty.empty

    def test_shape(self):
        assert arr.shape == (45, 2)
        assert arr_selected.shape == (1, 2)
        assert delegated.shape == (1, 2)
        assert associated.shape == (1, 2)

    def test_columns(self):
        assert arr.columns.tolist() == ["CODE", "PARENT"]

    def test_content(self):
        assert dict(arr_selected.values) == {"75101": "75056"}


# %% set_vintage
input_set_vintage = pd.DataFrame(
    [
        ["07180", "Fusion"],
        ["02077", "Commune déléguée"],
        ["02564", "Commune nouvelle"],
        ["75101", "Arrondissement municipal"],
        ["59298", "Commune associée"],
        ["99999", "Code erroné"],
        ["14472", "Oudon"],
        ["98799", "La Passion <= 2007"],
        ["98901", "La Passion > 2008"],
        ["97123", "Saint-Barthélemy <= 2007"],
        ["97701", "Saint-Barthélemy > 2008"],
        ["97127", "Saint-Martin <= 2007"],
        ["97801", "Saint-Martin > 2008"],
    ],
    columns=["A", "Test"],
    index=["A", "B", "C", "D", 1, 2, 3, 4, 5, 6, 7, 8, 9],
)
ouptut_set_vintage = set_vintage(input_set_vintage, 2023, field="A")


class test_set_vintage(TestCase):
    def test_class(self):
        assert isinstance(ouptut_set_vintage, pd.DataFrame)

    def test_shape(self):
        assert input_set_vintage.shape == ouptut_set_vintage.shape

    def test_columns(self):
        assert (input_set_vintage.columns == ouptut_set_vintage.columns).all()

    def test_indexes(self):
        assert (input_set_vintage.index == ouptut_set_vintage.index).all()

    def test_content(self):
        assert ouptut_set_vintage.A.to_dict() == {
            "A": "07204",
            "B": "02564",
            "C": "02564",
            "D": "75056",
            1: "59350",
            2: None,
            3: "14654",
            4: "98901",
            5: "98901",
            6: "97701",
            7: "97701",
            8: "97801",
            9: "97801",
        }
