# -*- coding: utf-8 -*-
"""
Created on Tue Jun 18 20:22:35 2024

@author: utilisateur
"""

import io
import numpy as np
import os
import pandas as pd
from requests_cache import CachedSession
from zipfile import zipfile

from french_cities import find_city

# # =============================================================================
# # Récupération du jeu de données 2022
# # =============================================================================
# url = "https://www.douane.gouv.fr/sites/default/files/openData/files/annuaire-des-debits-de-tabac-2018.zip"
# s = CachedSession()
# r = s.get(url)
# with zipfile.ZipFile(io.BytesIO(r.content)) as z:
#     content = z.read("annuaire-des-debits-de-tabac-2018.csv")
#     df = pd.read_csv(
#         io.BytesIO(content), dtype=str, sep=";", encoding="cp1252"
#     )


# # %%
# df = find_city(
#     df,
#     x=False,
#     y=False,
#     dep=False,
#     city="COMMUNE",
#     address="ADRESSE",
#     postcode="CODE POSTAL",
#     field_output="insee_com",
#     session=s,
#     use_nominatim_backend=True,
# )

# df.insee_com.value_counts()

url = "https://media.interieur.gouv.fr/rna/rna_import_20240601.zip"
s = CachedSession()
r = s.get(url)
with zipfile.ZipFile(io.BytesIO(r.content)) as z:
    df = pd.concat(
        [
            pd.read_csv(
                io.BytesIO(z.read(x.filename)),
                dtype=str,
                sep=";",
                encoding="utf8",
                quoting=1,  # quote all
            )
            for x in z.filelist
        ],
        ignore_index=True,
    )

print(df.info())

# Retraitement des codes postaux manifestement erronés
ix = df[~df.adrs_codepostal.fillna("").str.match("[0-9AB]{5}")].index
df.loc[ix, "adrs_codepostal"] = np.nan
df["adrs_codepostal"] = df["adrs_codepostal"].replace("00000", np.nan)


df = find_city(
    df,
    year="last",
    x=False,
    y=False,
    epsg=False,
    city="libcom",
    address=False,
    postcode="adrs_codepostal",
    use_nominatim_backend=True,
    field_output="codeInsee",
)
