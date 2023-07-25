# -*- coding: utf-8 -*-

from unittest import TestCase
import pandas as pd


from french_cities.departement_finder import find_departements

input_df = pd.DataFrame(
    {
        "code_postal": ["59800", "97133", "20000", "68013"],
        "code_commune": ["59350", "97701", "2A004", "68066"],
        "communes": ["Lille", "Saint-Barthélémy", "Ajaccio", "Colmar Cedex"],
        "deps": ["59", "977", "2A", "68"],
        
    }
)


class test_find_departements(TestCase):
    def test_from_post(self):
        test = find_departements(
            input_df, "code_postal", "dep_test", "postcode"
        )
        assert (test["dep_test"] == test["deps"]).all()

    def test_from_insee(self):
        test = find_departements(input_df, "code_commune", "dep_test", "insee")
        assert (test["dep_test"] == test["deps"]).all()
