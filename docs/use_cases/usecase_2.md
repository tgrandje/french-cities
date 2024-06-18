---
layout: default
title: Retrouver des codes communes à partir de codes postaux et libellés
language: fr
handle: /use_cases_2
parent: Cas d'usages
nav_order: 2

---

# Cas d'usage
## Retrouver des codes communes à partir de codes postaux et libellés de communes

Accéder <a href="./../usecase_2_notebook.html" target="_blank">au notebook ici</a>.

La qualité de l'opendata français continue à s'améliorer d'année en année et ce
cas d'usage devient aujourd'hui rare.
Ceci étant dit, on trouve toujours des jeux de données  (parfois historiques)
pour lesquels sont fournis des codes postaux et des libellés communaux (au lieu
de codes INSEE).

Dans cet exemple, on s'intéressera aux marchés publics conclus recensés sur la
plateforme des achats de l’Etat en 2015. Le jeu de données peut être retrouvé
[sur data.gouv.fr](https://www.data.gouv.fr/fr/datasets/marches-publics-conclus-recenses-sur-la-plateforme-des-achats-de-letat/)

### Dépendances utilisées dans ce projet
* openpyxl
* matplotlib (facultatif)
* pandas
* requests-cache
* french-cities

### Constitution du jeu de données

```python
import io
import numpy as np
import os
import pandas as pd
from requests_cache import CachedSession

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
```

### Reconnaissance des codes communes avec french-cities

```python
from french_cities import find_city

# =============================================================================
# Configuration de l'API INSEE
# =============================================================================
os.environ["insee_key"] = "********************"
os.environ["insee_secret"] = "********************"


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

>> codeInsee
False    11267
True       567
Name: count, dtype: int64
```

### Tracer un graphe des principaux montants agrégés à la commune de l'attributaire
```python
df["Montant"] = pd.to_numeric(df["Montant"].str.replace(",", ".").str.replace(" ", "")),
df.groupby("codeInsee")["Montant"].sum().sort_values(ascending=False).head(10).plot(kind="bar")
```