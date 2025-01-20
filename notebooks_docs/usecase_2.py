# -*- coding: utf-8 -*-
"""
Cas d'usage #2 : après récupération d'un jeu de données quelconque (ici les
marchés publics conclus recensés sur la plateforme des achats de l’Etat)
retrouver les codes communes des attributaires connaissant les libellés
communaux et les codes postaux
"""

import io
import numpy as np
import os
import pandas as pd
from requests_cache import CachedSession

from french_cities import find_city

# =============================================================================
# Récupération des marchés publics conclus
# =============================================================================
url = (
    "https://static.data.gouv.fr/"
    "resources/"
    "marches-publics-conclus-recenses-sur-la-plateforme-des-achats-de-letat/"
    "20160701-120733/Export_ETALAB_2015_complete.xlsx"
)
s = CachedSession()
r = s.get(url)
obj = io.BytesIO(r.content)
obj.seek(0)
df = pd.read_excel(obj)
for c in df.columns:
    try:
        df[c] = df[c].str.replace("^ *$", "", regex=True).replace("", None)
    except AttributeError:
        pass
df = df.dropna(how="all", axis=1)

# Retraitement des codes postaux manifestement erronés
ix = df[
    ~df["Code Postal Attributaire"].fillna("").str.fullmatch("[0-9]{5}")
].index
df.loc[ix, "Code Postal Attributaire"] = np.nan

# =============================================================================
# Configuration de l'API INSEE
# =============================================================================
os.environ["insee_key"] = "********************"
os.environ["insee_secret"] = "********************"

# =============================================================================
# Reconnaissance des codes communes avec french-cities
# =============================================================================

df = find_city(
    df,
    year="last",
    x=False,
    y=False,
    epsg=False,
    city="Ville",
    dep=False,
    address=False,
    postcode="Code Postal Attributaire",
    use_nominatim_backend=True,
    field_output="codeInsee",
)

print(df.codeInsee.isnull().value_counts())
