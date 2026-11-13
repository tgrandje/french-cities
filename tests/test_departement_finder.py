# -*- coding: utf-8 -*-

from unittest import TestCase
import io
import pandas as pd


from french_cities.departement_finder import find_departements

input_df = pd.DataFrame(
    {
        "code_postal": ["59800", "97200", "20000", "97133", "68013"],
        "code_commune": ["59350", "97209", "2A004", "97123", "68066"],
        "communes": [
            "Lille",
            "Fort-de-France",
            "Ajaccio",
            "Saint-Barthélemy",
            "Colmar Cedex",
        ],
        "deps": ["59", "972", "2A", "977", "68"],
    }
)

input_df2 = pd.DataFrame(
    {
        "deps": [
            "Charente-Maritime",
            "Seine-et-Marne",
            "Corse sud",
            "Alpe de Haute-Provence",
            "Aisne",
            "Ain",
        ],
        "codes": ["17", "77", "2A", "04", "02", "01"],
    }
)

input_df3 = pd.DataFrame(
    {
        "code_postal": ["02999"],
        "code_commune": ["02999"],
        "communes": ["Laon"],
        "deps": ["02"],
    }
)


class MockedHexasmalResponse:
    ok = True
    content = (
        "code_commune_insee;nom_de_la_commune;code_postal;libelle_d_acheminement;ligne_5;_geo_point\r\n"
        "59350;LILLE;59800;LILLE;;50.631080600000004,3.04684015\r\n"
        "97209;FORT DE FRANCE;97200;FORT DE FRANCE;;14.64924555,-61.0686332\r\n"
        "2A004;AJACCIO;20000;AJACCIO;;41.922694,8.705767250000001\r\n"
        "97701;ST BARTHELEMY;97133;ST BARTHELEMY;;\r\n"
    )
    df = pd.read_csv(io.StringIO(content), sep=";", dtype="str")
    content = df.to_parquet()


class MockedResponse:
    ok = True
    content = b"code_postal,result_context\r\n68013,\r\n"

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
        if "hexasmal" in args[0]:
            return MockedHexasmalResponse()
        else:
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
        test = find_departements(input_df2, "deps", "DEP_CODE", "label")
        assert (test["DEP_CODE"] == test["codes"]).all()

    def test_live_without_set_session(self):
        test = find_departements(
            input_df, "code_postal", "dep_test", "postcode"
        )
        assert (test["dep_test"] == test["deps"]).all()

    def test_last_resort(self):
        test = find_departements(
            input_df3, "code_postal", "dep_test", "postcode"
        )
        assert (test["dep_test"] == test["deps"]).all()
