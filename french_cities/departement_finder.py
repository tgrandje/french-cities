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


logger = logging.getLogger(__name__)


def _process_departements_from_postal(
    df: pd.DataFrame, source: str, alias: str, session: Session = None
) -> pd.DataFrame:
    """
    Méthode statique pour calculer un code département à partir d'un champ
    (code postal) et ajouter le résultat sous le nom de colonne 'alias'.
    Utilise la BAN pour interpréter les codes postaux

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame contenant des codes postaux
    source : str
        Colonne à utiliser pour calculer les codes département
    alias : str
        Nom de colonne où stocker le résultat
    session : Session, optional
        session web. The default is None (and will use a CachedSession with
        30 days expiration)

    Returns
    -------
    df : pd.DataFrame
        DataFrame enrichi du code département

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
    Méthode statique pour calculer un code département à partir d'un champ
    (code commune) et ajouter le résultat sous le nom de colonne 'alias'.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame contenant des codes communes
    source : str
        Colonne à utiliser pour calculer les codes département
    alias : str
        Nom de colonne où stocker le résultat
    session : Session, optional
        session web. The default is None (and will use a CachedSession with
        30 days expiration)
        **ignored argument, set only for coherence with
        _process_departements_from_postal**

    Returns
    -------
    df : pd.DataFrame
        DataFrame enrichi du code département

    """
    df[alias] = df[source].str[:2]

    ix = df[df[alias] == "97"].index
    df.loc[ix, alias] = df.loc[ix, source].str[:3]

    return df


def process_departements(
    df: pd.DataFrame,
    source: str,
    alias: str,
    type_code: str,
    session: Session = None,
) -> pd.DataFrame:
    """
    Méthode statique pour calculer un code département à partir d'un champ
    (code commune ou code postal) et ajouter le résultat sous le nom de colonne
    'alias'.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame contenant des codes communes
    source : str
        Colonne à utiliser pour calculer les codes département
    alias : str
        Nom de colonne où stocker le résultat
    type_code : str
        Type de champ soumis à l'algorithme : code commune ('insee') ou
        code postal ('postcode')
    session : Session, optional
        session web. The default is None (and will use a CachedSession with
        30 days expiration)

    Raises
    ------
    ValueError
        If type_code not among "postcode", "insee".

    Returns
    -------
    df : pd.DataFrame
        DataFrame enrichi du code département

    """
    if type_code not in {"postcode", "insee"}:
        msg = (
            "type_code must be among ('postcode', 'insee') - "
            f"found {type_code} instead"
        )
        raise ValueError(msg)
    df = df.copy()
    if type_code == "postcode":
        func = _process_departements_from_postal
    elif type_code == "insee":
        func = _process_departements_from_insee_code
    return func(df, source, alias, session)
