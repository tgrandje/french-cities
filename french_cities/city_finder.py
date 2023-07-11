# -*- coding: utf-8 -*-
"""
Created on Thu Jul  6 11:38:34 2023

@author: thomas.grandjean
"""
import pandas as pd
import io
import logging
from requests_cache import CachedSession
from requests import Session
from rapidfuzz import fuzz
import unidecode
from pynsee.geodata import get_geodata
import geopandas as gpd
from pyproj import Transformer
from datetime import date

from french_cities.vintage import set_vintage
from french_cities.departement_finder import process_departements


logger = logging.getLogger(__name__)


def _find_from_geoloc(
    epsg: int,
    df: pd.DataFrame,
    year: str = "last",
    field_output: str = "insee_com",
) -> pd.DataFrame:
    """
    Find cities codes from coordinates using a spatial join.

    Note that the result will be approximative as the IGN's WFS data is not
    vintaged (yet ?). The spatial join will then be computed against latest
    available data. A reprojection in the desired vintage will be done
    afterwards, but cities joined during this lapse time will NOT be correctly
    found.

    Parameters
    ----------
    epsg : int
        EPSG code of projection
    df : pd.DataFrame
        input DataFrame. Must have an 'x' and an 'y' columns containing points
    year : str, optional
        Desired vintage for cities; must a castable value to int or "last".
        The default is "last".
    field_output : str, optional
        Column to store the cities code into. The default is "insee_com".

    Raises
    ------
    ValueError
        If year not castable to int, or not "last".

    Returns
    -------
    df : pd.DataFrame
        output DataFrame with `field_output` containing cities' codes

    """

    if year != "last":
        try:
            int(year)
        except ValueError:
            raise ValueError(
                "year should either be castable to int or 'last', "
                f"found {year} instead"
            )

    if year not in {str(date.today().year), "last"}:
        logger.warning(
            "As of yet, ADMINEXPRESS can't be fetched with a vintage "
            "setting: the querying of cities using coordinates WILL have "
            "approximative results."
        )

    com = get_geodata("ADMINEXPRESS-COG-CARTO.LATEST:commune")
    com = gpd.GeoDataFrame(com).set_crs("EPSG:3857")

    transformer = Transformer.from_crs(epsg, 3857, accuracy=1, always_xy=True)

    temp = transformer.transform(df["x"].tolist(), df["y"].tolist())
    temp = gpd.GeoSeries(
        gpd.points_from_xy(x=temp[0], y=temp[1], crs=3857),
        name="geometry",
        index=df.index,
    )

    df = gpd.GeoDataFrame(temp.to_frame().join(df), crs=3857)
    df = df.sjoin(com[["insee_com", "geometry"]], how="left")
    df = df.drop(["geometry", "index_right"], axis=1)

    if year not in {str(date.today().year), "last"}:
        year = int(year)
        df = set_vintage(df, year, "insee_com")
    return df


def find_city(
    df: pd.DataFrame,
    year: str = "last",
    field_output: str = "insee_com",
    epsg: int = None,
    session: Session = None,
) -> pd.DataFrame:
    """
    TODO
    Possible avec colonnes :
        x & y (si epsg fourni)
        dep & township
        postal_code & township
        address, postal_code & township


    """

    logger.debug("finding from addresses ")

    columns = set(df.columns)
    necessary1 = {"postal_code", "township"}
    necessary2 = {"dep", "township"}
    necessary3 = {"x", "y"}
    if not any(
        len(x - columns) == 0 for x in (necessary1, necessary2, necessary3)
    ):
        msg = (
            f"All columns among {necessary1}, {necessary2} OR {necessary3} "
            "are necessary"
        )
        raise ValueError(msg)

    if not session:
        session = CachedSession(allowable_methods=("GET", "POST"))

    # User geolocation first
    if len(necessary3 - columns) == 0 and epsg:
        # On peut travailler à partir de la géoloc
        df = _find_from_geoloc(epsg, df, year, field_output).rename(
            {field_output: "candidat_0"}, axis=1
        )

    # Preprocess cities names
    if "township" in set(df.columns):
        df["township_cleaned"] = (
            df["township"]
            .str.replace(
                r" \(.*\)$", "", regex=True
            )  # Neuville-Housset (La) -> Neuville-Housset
            .str.upper()
            .apply(unidecode)  # A voir si on conserve
            .str.split("\W+")
            .str.join(" ")
        )

    # Control which configuration can be used
    # Note that the order is relevant here, as this will determine the result's
    # preference
    to_test_ok = []
    to_test = [
        ("postal_code", "township_cleaned"),
        ("address", "postal_code", "township_cleaned"),
        ("dep", "township_cleaned"),
    ]
    for x in to_test:
        try:
            df.loc[:, x]
        except KeyError:
            pass
        else:
            to_test_ok.append(x)

    components_kept = list({y for x in to_test_ok for y in x})

    addresses = df.loc[:, components_kept].drop_duplicates().fillna("")

    # Add dep recognition if not already there, just to check the result's
    # coherence (and NOT to compute city recognition using it!)
    if "dep" not in components_kept:
        addresses = process_departements(
            addresses, "postal_code", "dep", "postoffice", session
        )

    for k, components in enumerate(to_test_ok):
        # TODO

        def list_map(df, columns):
            "https://stackoverflow.com/questions/39291499#answer-62135779"
            return pd.Series(
                map(" ".join, df[columns].values.tolist()), index=df.index
            )

        addresses = (list_map(addresses.copy(), components).to_frame("full"),)
        addresses = addresses.drop_duplicates(keep="first")

        logger.info(f"request BAN with {components}...")
        r = session.post(
            # recherche "en masse" grâce à l'API de la BAN
            "https://api-adresse.data.gouv.fr/search/csv/",
            files=[
                ("data", addresses.to_csv(index=False)),
                ("result_columns", (None, "full")),
                ("result_columns", (None, "result_score")),
                ("result_columns", (None, "result_city")),
                ("result_columns", (None, "result_citycode")),
            ],
        )

        logger.info("résultat obtenu")

        results_api = (
            pd.read_csv(io.BytesIO(r.content), dtype={"result_citycode": str})
            .drop_duplicates()
            .loc[:, ["full", "result_score", "result_city", "result_citycode"]]
            .merge(
                addresses[["dep", "full", "township"]].drop_duplicates(),
                on="full",
            )
        )

        # Contrôle de cohérence : même département
        results_api = process_departements(
            results_api, "result_citycode", "result_dep", "insee", session
        )
        ix = results_api[results_api.dep == results_api.result_dep].index
        results_api = results_api.loc[ix]

        # TODO
        # Contrôle de cohérence : fuzzy matching sur nom commune
        results_api["result_city"] = (
            results_api["result_city"]
            .str.upper()
            .apply(unidecode)
            .str.split(r"\W+")
            .str.join(" ")
        )
        results_api["score"] = results_api[["township", "result_city"]].apply(
            lambda xy: fuzz.token_set_ratio(*xy)
        )

        ix = results_api[
            # Either a good fuzzy match
            ((results_api["township"] != "") & (results_api["score"] > 80))
            # Or a good match on BAN (case of cities fusion for instance):
            | (results_api["township"] != "")
            & (results_api["result_score"] > 0.6)
            # Or a goodish match on BAN but no available city label:
            | (results_api["township"] == "")
            & (results_api["result_score"] > 0.4)
        ].index

        results_api = results_api.loc[ix, ["full", "result_citycode"]].rename(
            {"result_citycode": f"candidat_{k+1}"}, axis=1
        )
        addresses = addresses.merge(results_api, on="full", how="left")

    # TODO
    addresses = addresses.with_columns(
        pl.coalesce(
            [f"candidat_{k}" for k in range(len(components_tested) + 1)]
        )
        .cast(pl.Categorical)
        .alias("INSEE_COMMUNE")
    ).select(components_kept + ["INSEE_COMMUNE"])

    df = df.join(addresses, how="left", on=components_kept)
    return pd.DataFrame(df)
