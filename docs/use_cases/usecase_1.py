# -*- coding: utf-8 -*-
"""
Cas d'usage #1 : après récupération d'un jeu de données quelconque (ici les
industries classées pour la protection de l'environnement de la région
Hauts-de-France), l'objectif est de retrouver les codes communes manquants
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
print(data.head())
print(data.shape)
print("-" * 50)
print("Codes INSEE manquants :")
print(data.codeInsee.isnull().value_counts())
print("-" * 50)

# =============================================================================
# Utilisation de french-cities pour trouver les codes communes manquants
# =============================================================================

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
    use_nominatim_backend=False,
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

print(
    "A date du 30/05/2024, une seule commune n'a pas été trouvée. "
    "Effectivement, dans ce cas de figure, le lieu-dit (PONT DE BRIQUES) et "
    "la commune (SAINT ETIENNE AU MONT) ont été inversés : ceci explique "
    "que le score de la base adresse nationale n'ait pas été jugé "
    "suffisamment bon pour que le résultat de Saint-Etienne-au-Mont être "
    "retenu..."
)

print("-" * 50)
# =============================================================================
print(
    "Si cette fois, on décide d'utiliser l'API Nominatim en dernier "
    "recours, on obtient :"
)
print("-" * 50)
print("nouvel essai avec Nominatim :")
missing = data[data.codeInsee.isnull()]
# Concaténer les champs adresses :
cols = [f"adresse{x}" for x in range(1, 4)]
missing["adresse"] = (
    missing[cols[0]]
    .str.cat(missing[cols[1:]], sep=" ", na_rep="")
    .str.replace(" +", " ", regex=True)
    .str.strip(" ")
)
missing = find_city(
    missing,
    year="last",
    x="coordonneeXAIOT",
    y="coordonneeYAIOT",
    epsg=2154,
    city="commune",
    address="adresse",
    postcode="codePostal",
    use_nominatim_backend=True,
    field_output="newCodeInsee",
)
print(missing["newCodeInsee"])
print(
    "L'exécution de Nominatim ne conduit pas systématiquement au même résultat"
    ", ce qui n'est pas totalement absurde, le hameau manquant étant à cheval "
    "sur plusieurs communes. Les résultats fournis sont normalement tous "
    "pertinents."
)
