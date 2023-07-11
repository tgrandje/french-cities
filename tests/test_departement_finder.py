# -*- coding: utf-8 -*-

from unittest import TestCase
import pandas as pd


from french_cities.departement_finder import process_departements


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
        test = process_departements(
            self.input, "code_postal", "dep_test", "postcode"
        )
        assert (test["dep_test"] == test["deps"]).all()

    def test_from_insee(self):
        test = process_departements(
            self.input, "code_commune", "dep_test", "insee"
        )
        assert (test["dep_test"] == test["deps"]).all()


# from french_cities.city_finder import (
#     from_postal_code,
#     from_postal_code_city_label,
#     from_city_label,
#     from_geoloc,
#     from_address,
# )


# def test_from_postal_code_1():
#     "needs a pd.Series as input"
#     match = "excepted pd.Series"
#     with pytest.raises(ValueError, match=match):
#         from_postal_code("02000")


# def test_from_postal_code_2():
#     """or needs a pd.DataFrame with "postal_code" in columns"""
#     match = "missing postal_code"
#     with pytest.raises(ValueError, match=match):
#         from_postal_code(pd.DataFrame([["59000"]], columns=["dummy"]))


# def test_from_postal_code_3():
#     "returns a pd.Series"
#     assert (
#         isinstance(from_postal_code(pd.Series(["59000"])), pd.Series)
#     ) and isinstance(
#         from_postal_code(pd.DataFrame([["59000"]], columns=["postal_code"])),
#         pd.Series,
#     )


# def test_from_postal_code_4():
#     "raises a warning if dtype is not str"
#     match = "strings"
#     with pytest.warns(match=match):
#         # s.apply(type).eq(str).all()
#         from_postal_code(pd.Series([59000]))


# def test_from_postal_code_5():
#     """
#     displays a warning if all codes are not matching the 5 digits when casted
#     to strings
#     """
#     match = "5-digits length"
#     with pytest.warns(match=match):
#         # s.apply(type).eq(str).all()
#         from_postal_code(pd.Series([2000]))


# def test_from_postal_code_6():
#     "returns excepted results"
#     test1 = from_postal_code(pd.Series(["59000"])).tolist() == ["59350"]
#     test2 = from_postal_code(pd.Series(["20000"])).tolist() == ["2A004"]
#     test3 = from_postal_code(pd.Series(["75013"])).tolist() == ["75056"]
#     assert test1 & test2 & test3


# def test_from_postal_code_7():
#     "preserves shape and index"
#     s = pd.Series(["59000", "59000"], index=["a", "b"])
#     assert (from_postal_code(s).index == s.index).all()


# def test_from_postal_code_8():
#     """
#     raises a warning when using a wrong postal code and returns NaN (for the
#     given row)
#     """
#     match = "unknown postal code"
#     with pytest.warngs(match=match):
#         result = from_postal_code(pd.Series(["98999", "59000"]))
#     assert result.isnull().iloc[0] and not result.isnull().iloc[1]


# def test_from_postal_code_cities_label():
#     """
#     Recognition from postal_code and city_label
#     * needs a pd.DataFrame with "postal_code" and "city" in columns
#     * returns a pd.Series
#     * returns expected results
#     * returns expected results even on obsolete cities
#     * preserves shape and index
#     * handles Cedex codes
#     * raises a warning when postal code and city label are incoherent and
#       gives preference to the city label
#     * raises a warning when using a couple of wrong postal code AND city
#       label, returns NaN on given row
#     """
#     pass


# def test_from_postal_code_cities_label_1():
#     """needs a pd.DataFrame with "postal_code" and "city" in columns"""
#     match = "missing postal_code"
#     with pytest.raises(ValueError, match=match):
#         cols = ["dummy", "city"]
#         df = pd.DataFrame([["59000", "Lille"]], columns=cols)
#         from_postal_code_city_label(df)


# def test_from_postal_code_cities_label_2():
#     """needs a pd.DataFrame with "postal_code" and "city" in columns"""
#     match = "missing city"
#     with pytest.raises(ValueError, match=match):
#         cols = ["postal_code", "dummy"]
#         df = pd.DataFrame([["59000", "Lille"]], columns=cols)
#         from_postal_code_city_label(df)


# def test_from_postal_code_cities_label_3():
#     "returns a pd.Series"
#     cols = ["postal_code", "city"]
#     df = pd.DataFrame([["59000", "Lille"]], columns=cols)
#     assert isinstance(from_postal_code_city_label(df), pd.Series)


# def test_from_postal_code_cities_label_4():
#     "returns excepted results"

#     cols = ["postal_code", "city"]
#     df = pd.DataFrame([["59000", "Lille"]], columns=cols)
#     test1 = from_postal_code(df).tolist() == ["59350"]

#     df = pd.DataFrame([["20000", "Ajaccio"]], columns=cols)
#     test2 = from_postal_code_city_label(df).tolist() == ["2A004"]

#     df = pd.DataFrame([["75013", "Paris"]], columns=cols)
#     test3 = from_postal_code_city_label(df).tolist() == ["75056"]

#     assert test1 & test2 & test3


# def test_from_postal_code_cities_label_5():
#     "returns expected results even on obsolete cities"
#     cols = ["postal_code", "city"]
#     df = pd.DataFrame([["02200", "Berzy-le-Sec"]], columns=cols)
#     assert from_postal_code_city_label(df).tolist() == ["02564"]


# def test_from_postal_code_cities_label_6():
#     "returns expected results even on newests cities"
#     # TODO : récupérer les toutes dernières communes
#     cols = ["postal_code", "city"]
#     df = pd.DataFrame([["02200", "Bernoy le Château"]], columns=cols)
#     assert from_postal_code_city_label(df).tolist() == ["02564"]


# def test_from_postal_code_cities_label_7():
#     "preserves shape and index"
#     cols = ["postal_code", "city"]
#     df = pd.DataFrame(
#         [["59000", "Lille"], ["59000", "Lille"]],
#         columns=cols,
#         index=["a", "b"],
#     )
#     assert (from_postal_code(df).index == df.index).all()


# def test_from_postal_code_cities_label_8():
#     "handles Cedex codes"
#     cols = ["postal_code", "city"]
#     df = pd.DataFrame([["59019", "LILLE cedex"]], columns=cols)
#     assert from_postal_code_city_label(df).tolist() == ["59350"]


# def test_from_postal_code_cities_label_9():
#     """
#     raises a warning when postal code and city label are incoherent and
#     gives preference to the city label
#     """
#     cols = ["postal_code", "city"]
#     df = pd.DataFrame([["59000", "Paris"]], columns=cols)
#     match = "incoherent"
#     with pytest.warns(match=match):
#         assert from_postal_code_city_label(df).tolist() == ["75056"]


# def test_from_postal_code_cities_label_10():
#     """
#     raises a warning when using a couple of wrong postal code AND city
#     label, returns NaN on given row
#     """
#     cols = ["postal_code", "city"]
#     df = pd.DataFrame([["98999", "Dummy"], ["59000", "Lille"]], columns=cols)
#     match = "unknown postal code and city"
#     with pytest.warns(match=match):
#         result = from_postal_code(df)
#         assert result.isnull().iloc[0] and not result.isnull().iloc[1]


# def test_from_postal_code_cities_label_11():
#     "handles simple spelling mistakes"
#     cols = ["postal_code", "city"]
#     df = pd.DataFrame([["59000", "Llile"], ["02000", "Loan"]], columns=cols)
#     result = from_postal_code(df)
#     assert result.tolist() == ["59350", "02408"]


# def test_from_city_label_1():
#     "needs a pd.Series as input"
#     pass
