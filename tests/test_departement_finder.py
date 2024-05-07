# -*- coding: utf-8 -*-

from unittest import TestCase
import pandas as pd


from french_cities.departement_finder import (
    find_departements,
    find_departements_from_names,
)

input_df = pd.DataFrame(
    {
        "code_postal": ["59800", "97133", "20000", "68013"],
        "code_commune": ["59350", "97701", "2A004", "68066"],
        "communes": ["Lille", "Saint-Barthélémy", "Ajaccio", "Colmar Cedex"],
        "deps": ["59", "977", "2A", "68"],
    }
)

input_df2 = pd.DataFrame(
    {
        "deps": ["Corse sud", "Alpe de Haute-Provence", "Aisne", "Ain"],
        "codes": ["2A", "04", "02", "01"],
    }
)


class MockedResponse:
    ok = True
    content = (
        b"code_postal,result_context\r\n"
        b'59800,"59, Nord, Hauts-de-France"\r\n'
        b'97133,"977, Saint-Barth\xc3\xa9lemy"\r\n'
        b'20000,"2A, Corse-du-Sud, Corse"\r\n'
        b"68013,\r\n"
    )

    def json(self):
        return {
            "total_count": 1,
            "results": [
                {
                    "insee": "68066",
                    "libelle": "COLMAR CEDEX",
                    "nom_com": "Colmar",
                }
            ],
        }


class MockedSession:
    def post(self, *args, **kwargs):
        return MockedResponse()

    def get(self, *args, **kwargs):
        return MockedResponse()


class test_find_departements(TestCase):
    def test_from_post(self):
        test = find_departements(
            input_df,
            "code_postal",
            "dep_test",
            "postcode",
            session=MockedSession(),
        )
        assert (test["dep_test"] == test["deps"]).all()

    def test_from_insee(self):
        test = find_departements(
            input_df,
            "code_commune",
            "dep_test",
            "insee",
            session=MockedSession(),
        )
        assert (test["dep_test"] == test["deps"]).all()

    def test_from_name(self):
        test = find_departements_from_names(
            input_df2,
            "deps",
        )
        assert (test["DEP_CODE"] == test["codes"]).all()
