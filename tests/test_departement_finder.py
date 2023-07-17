# -*- coding: utf-8 -*-

from unittest import TestCase
import pandas as pd


from french_cities.departement_finder import find_departements


class test_find_departements(TestCase):
    def setUp(self):
        self.input = pd.DataFrame(
            {
                "code_postal": ["59800", "97133", "20000"],
                "code_commune": ["59350", "97701", "2A004"],
                "communes": ["Lille", "Saint-Barthélémy", "Ajaccio"],
                "deps": ["59", "977", "2A"],
            }
        )

    def test_from_post(self):
        test = find_departements(
            self.input, "code_postal", "dep_test", "postcode"
        )
        assert (test["dep_test"] == test["deps"]).all()

    def test_from_insee(self):
        test = find_departements(
            self.input, "code_commune", "dep_test", "insee"
        )
        assert (test["dep_test"] == test["deps"]).all()
