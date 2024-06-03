# -*- coding: utf-8 -*-
"""
Cas d'usage #2 : après récupération d'un jeu de données quelconque (ici les
l'annuaire des débits de tabac en France métropolitaine),
retrouver les codes communes des établissements connaissant les libellés
communaux et les codes postaux
"""

import io
import os
import pandas as pd
from requests_cache import CachedSession
import zipfile

from french_cities import find_departements, find_city

# =============================================================================
# Configuration de l'API INSEE
# =============================================================================
os.environ["insee_key"] = "********************"
os.environ["insee_secret"] = "********************"

# =============================================================================
# Récupération du jeu de données 2022
# =============================================================================
url = "https://www.douane.gouv.fr/sites/default/files/openData/files/annuaire-des-debits-de-tabac-2018.zip"
s = CachedSession()
r = s.get(url)
with zipfile.ZipFile(io.BytesIO(r.content)) as z:
    content = z.read("annuaire-des-debits-de-tabac-2018.csv")
    df = pd.read_csv(
        io.BytesIO(content), dtype=str, sep=";", encoding="cp1252"
    )


# %%
df = find_departements(
    df, source="CODE POSTAL", alias="DEP", type_code="postcode", session=s
)
# %%
df = find_city(
    df,
    x=False,
    y=False,
    dep="DEP",
    city="COMMUNE",
    address="ADRESSE",
    postcode="CODE POSTAL",
    field_output="insee_com",
    session=s,
    use_nominatim_backend=True,
)

df.insee_com.value_counts()
