# -*- coding: utf-8 -*-
"""
Created on Mon May 27 20:17:56 2024

@author: utilisateur
"""

import os
import pandas as pd
from requests_cache import CachedSession
from tqdm import tqdm

from french_cities import find_city

# =============================================================================
# Configuration de l'API INSEE
# =============================================================================
os.environ["insee_key"] = "********************"
os.environ["insee_secret"] = "********************"

# =============================================================================
# Récupération des ICPE de la région Hauts-de-France
# =============================================================================
code_region = "32"
page_size = 1000

s = CachedSession()
r = s.get(
    "https://georisques.gouv.fr/api/v1/installations_classees",
    params={"page": "1", "page_size": page_size, "region": code_region},
)
number_pages = r.json()["total_pages"]
for x in tqdm(range(number_pages), desc="querying georisques"):
    try:
        data
    except NameError:
        data = []
    else:
        r = s.get(
            "https://georisques.gouv.fr/api/v1/installations_classees",
            params={
                "page": x + 1,
                "page_size": page_size,
                "region": code_region,
            },
        )
    finally:
        data += r.json()["data"]
    if not r.json()["next"]:
        break
data = pd.DataFrame(data)

# =============================================================================
# ICPE dépourvues de codes communes INSEE :
# =============================================================================
print("-" * 50)
print("Codes INSEE manquants :")
print(data.codeInsee.isnull().value_counts())
print("-" * 50)

missing = data[data.codeInsee.isnull()]

# Au besoin, vérifier que le système de projection des coordonnées est en
# EPSG 2154
# print(missing.systemeCoordonneesAIOT.unique())

# Concaténer les champs adresses :
cols = [f"adresse{x}" for x in range(1, 4)]
missing["adresse"] = (
    missing[cols[0]]
    .str.cat(missing[cols[1:]], sep=" ", na_rep="")
    .str.replace(" +", " ", regex=True)
    .str.strip(" ")
)

# Recherche des communes manquantes à l'aide de french-cities
missing = find_city(
    missing,
    year="last",
    x="coordonneeXAIOT",
    y="coordonneeYAIOT",
    epsg=2154,
    city="commune",
    address="adresse",
    postcode="codePostal",
    field_output="newCodeInsee",
)

# Réinjection les codes manquants dans le dataframe comple
data = data.join(missing[["newCodeInsee"]])
data["codeInsee"] = data["codeInsee"].combine_first(data["newCodeInsee"])
data = data.drop("newCodeInsee", axis=1)

print("-" * 50)
print("Codes INSEE manquants après utilisation du package:")
print(data.codeInsee.isnull().value_counts())
print("-" * 50)


print("Données toujours manquantes:")
print(data[data.codeInsee.isnull()])

# data["codes_init"] = data["codeInsee"]
# data = set_vintage(data, year=date.today().year, field="codeInsee")
# print(data[data.codes_init != data.codeInsee])
