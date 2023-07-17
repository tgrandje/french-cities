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
        assert dict(self.cities.values) == {"02564": "02564", "02077": "02564"}


class test_get_cities_year(TestCase):
    def setUp(self):
        self.cities = _get_cities_year(2023)

    def test_class(self):
        assert isinstance(self.cities, pd.DataFrame)

    def test_shape(self):
        assert self.cities.shape == (34945, 1)

    def test_columns(self):
        assert self.cities.columns == ["CODE"]

    def test_content(self):
        assert "01001" in set(self.cities["CODE"])


class test_get_subareas_year(TestCase):
    def setUp(self):
        self.arr = _get_subareas_year("arrondissementsMunicipaux", 2023)
        self.arr_selected = _get_subareas_year(
            "arrondissementsMunicipaux", 2023, look_for=["75101"]
        )
        self.delegated = _get_subareas_year(
            "communesDeleguees", 2023, look_for={"01039"}
        )
        self.associated = _get_subareas_year(
            "communesAssociees", 2023, look_for={"59298"}
        )
        self.empty = _get_subareas_year(
            "communesAssociees", 2023, look_for={"59350"}
        )

    def test_class(self):
        assert isinstance(self.arr, pd.DataFrame)
        assert isinstance(self.delegated, pd.DataFrame)
        assert isinstance(self.associated, pd.DataFrame)
        assert isinstance(self.arr_selected, pd.DataFrame)
        assert isinstance(self.empty, pd.DataFrame)

    def test_error(self):
        assert self.empty.empty

    def test_shape(self):
        assert self.arr.shape == (45, 2)
        assert self.arr_selected.shape == (1, 2)
        assert self.delegated.shape == (1, 2)
        assert self.associated.shape == (1, 2)

    def test_columns(self):
        assert self.arr.columns.tolist() == ["CODE", "PARENT"]

    def test_content(self):
        assert dict(self.arr_selected.values) == {"75101": "75056"}


class test_set_vintage(TestCase):
    def setUp(self):
        self.input = pd.DataFrame(
            [
                ["07180", "Fusion"],
                ["02077", "Commune déléguée"],
                ["02564", "Commune nouvelle"],
                ["75101", "Arrondissement municipal"],
                ["59298", "Commune associée"],
                ["99999", "Code erroné"],
                ["14472", "Oudon"],
            ],
            columns=["A", "Test"],
            index=["A", "B", "C", "D", 1, 2, 3],
        )
        self.output = set_vintage(self.input, 2023, field="A")

    def test_class(self):
        assert isinstance(self.output, pd.DataFrame)

    def test_shape(self):
        assert self.input.shape == self.output.shape

    def test_columns(self):
        assert (self.input.columns == self.output.columns).all()

    def test_indexes(self):
        assert (self.input.index == self.output.index).all()

    def test_content(self):
        assert self.output.A.to_dict() == {
            "A": "07204",
            "B": "02564",
            "C": "02564",
            "D": "75056",
            1: "59350",
            2: None,
            3: "14654",
        }
