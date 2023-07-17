# -*- coding: utf-8 -*-
"""
Created on Thu Jul  6 11:38:34 2023
"""
import pandas as pd
import io
from requests_cache import CachedSession
from requests import Session
from datetime import timedelta
import logging

from french_cities.utils import init_pynsee


logger = logging.getLogger(__name__)


def _process_departements_from_postal(
    df: pd.DataFrame, source: str, alias: str, session: Session = None
) -> pd.DataFrame:
    """
    Retrieve departement's code from postoffice code. Adds the result as a new
    column to dataframe under the label 'alias'. Uses the BAN (Base Adresse
    Nationale under the hood).

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing postal codes
    source : str
        Field containing the postal codes
    alias : str
        Column to store the departements' codes unto
    session : Session, optional
        Web session. The default is None (and will use a CachedSession with
        30 days expiration)

    Returns
    -------
    df : pd.DataFrame
        Updated DataFrame with departement's codes

    """

    if not session:
        session = CachedSession(
            allowable_methods=("GET", "POST"), expire_after=timedelta(days=30)
        )

    postal_codes = df[[source]].drop_duplicates(keep="first")

    r = session.post(
        # recherche grâce à l'API de la BAN
        "https://api-adresse.data.gouv.fr/search/csv/",
        files=[
            ("data", postal_codes.to_csv(index=False)),
            ("postcode", (None, source)),
            ("result_columns", (None, source)),
            ("result_columns", (None, "result_context")),
        ],
    )
    result = pd.read_csv(io.BytesIO(r.content), dtype=str)
    result[alias] = (
        result["result_context"].str.split(",", expand=True)[0].str.strip(" ")
    )
    result = result.drop("result_context", axis=1)

    logger.info("résultat obtenu")

    df = df.merge(result, on=source, how="left")

    return df


def _process_departements_from_insee_code(
    df: pd.DataFrame, source: str, alias: str, session: Session = None
) -> pd.DataFrame:
    """
    Compute departement's codes from official french cities codes (COG INSEE).
    Adds the result as a new column to dataframe under the label 'alias'.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing official cities codes
    source : str
        Field containing the official codes (INSEE COG)
    alias : str
        Column to store the departements' codes unto
    session : Session, optional
        Web session. The default is None (and will use a CachedSession with
        30 days expiration)
        **ignored argument, set only for coherence with
        _process_departements_from_postal**

    Returns
    -------
    df : pd.DataFrame
        Updated DataFrame with departement's codes

    """
    df[alias] = df[source].str[:2]

    ix = df[df[alias] == "97"].index
    df.loc[ix, alias] = df.loc[ix, source].str[:3]

    return df


def find_departements(
    df: pd.DataFrame,
    source: str,
    alias: str,
    type_code: str,
    session: Session = None,
) -> pd.DataFrame:
    """
    Compute departement's codes from postal or official codes (ie. INSEE COG)'
    Adds the result as a new column to dataframe under the label 'alias'.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing official cities codes
    source : str
        Field containing the post or official codes
    alias : str
        Column to store the departements' codes unto
    type_code : str
        Type of codes passed under `alias` label. Should be either 'insee' for
        official codes or 'postcode' for postal codes.
    session : Session, optional
        Web session. The default is None (and will use a CachedSession with
        30 days expiration)

    Raises
    ------
    ValueError
        If type_code not among "postcode", "insee".

    Returns
    -------
    df : pd.DataFrame
        Updated DataFrame with departement's codes

    """
    if type_code not in {"postcode", "insee"}:
        msg = (
            "type_code must be among ('postcode', 'insee') - "
            f"found {type_code} instead"
        )
        raise ValueError(msg)

    init_pynsee()

    df = df.copy()
    if type_code == "postcode":
        func = _process_departements_from_postal
    elif type_code == "insee":
        func = _process_departements_from_insee_code
    return func(df, source, alias, session)
