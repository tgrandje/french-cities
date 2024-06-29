# -*- coding: utf-8 -*-
"""
Created on Thu Jun 20 07:39:35 2024

@author: utilisateur

Les sites pollués gérés par l’ADEME

"""

import io
import os
import pandas as pd
from requests_cache import CachedSession

from french_cities import set_vintage

# =============================================================================
# Configuration de l'API INSEE
# =============================================================================
os.environ["insee_key"] = "********************"
os.environ["insee_secret"] = "********************"


s = CachedSession()

url = "https://data.ademe.fr/data-fair/api/v1/datasets/srd-ademe/lines?size=10000&page=1&format=csv"

r = s.get(url)
df = pd.read_csv(io.BytesIO(r.content), sep=",", dtype=str)

ix = df[df.Code_INSEE.str.len() == 4].index
print(df.loc[ix, "Code_INSEE"])
df["Code_INSEE"] = df["Code_INSEE"].str.zfill(5)
print(df.loc[ix, "Code_INSEE"])

init = df["Code_INSEE"].copy()
init.name = "initial"

df = set_vintage(df, 2024, "Code_INSEE")

new = df["Code_INSEE"].copy()
new.name = "final"

print((init == new).all())
ix = init[init != new].index

print(init.to_frame().join(new).loc[ix])
