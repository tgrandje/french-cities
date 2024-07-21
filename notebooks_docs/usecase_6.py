# -*- coding: utf-8 -*-
"""
Created on Fri Jun 28 22:05:19 2024

@author: utilisateur
"""

import io
import pandas as pd
from requests_cache import CachedSession
from zipfile import ZipFile

from french_cities import find_city

# =============================================================================
# Récupération du jeu de données 2022
# =============================================================================
url = "https://www.douane.gouv.fr/sites/default/files/openData/files/annuaire-des-debits-de-tabac-2018.zip"
s = CachedSession()
r = s.get(url)
with ZipFile(io.BytesIO(r.content)) as z:
    content = z.read("annuaire-des-debits-de-tabac-2018.csv")
    df = pd.read_csv(
        io.BytesIO(content), dtype=str, sep=";", encoding="cp1252"
    )


# %%
df = find_city(
    df,
    x=False,
    y=False,
    dep=False,
    city="COMMUNE",
    address="ADRESSE",
    postcode="CODE POSTAL",
    field_output="insee_com",
    session=s,
    use_nominatim_backend=True,
)

df.insee_com.value_counts()

print(df[df.insee_com.isnull()])
print(
    "Une seule commune n'a pas été reconnue (OCCHIATANA en Haute-Corse). "
    "En effet, une erreur de saisie existe sur le code postal qui renvoie"
    "sur le mauvais département (20182 est un code CEDEX réel de Corse du "
    "Sud), ce qui induit l'algorithme en erreur."
)
