# -*- coding: utf-8 -*-
"""
Cas d'usage #3 : après récupération d'un arrêté "catastrophes naturelles",
retrouver des codes communes à partir de libellés communaux et départementaux
"""

import os
import pandas as pd
from requests_cache import CachedSession


from french_cities import find_departements, find_city

# =============================================================================
# Configuration de l'API INSEE
# =============================================================================
os.environ["insee_key"] = "********************"
os.environ["insee_secret"] = "********************"

# =============================================================================
# Récupération de l'arrêté "CATNAT" et chargement de l'annexe 1
# =============================================================================
url = "https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000048393151"
s = CachedSession()
FIREFOX = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) "
    "Gecko/20100101 Firefox/126.0"
)
s.headers.update({"User-Agent": FIREFOX})
r = s.get(url)
df = pd.read_html(r.content, encoding="utf8")[0]

# =============================================================================
# Reconnaissance des départements, puis des communes
# =============================================================================
df = find_departements(
    df, source="Département", alias="DEP_CODE", type_field="label"
)
df = find_city(
    df,
    x=False,
    y=False,
    dep="DEP_CODE",
    city="Commune",
    address=False,
    postcode=False,
    session=s,
)

# =============================================================================
# Analyse des résultats
# =============================================================================
print(df[["DEP_CODE", "insee_com"]].info())
