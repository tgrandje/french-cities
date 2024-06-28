---
layout: default
title: Millésimer un jeu de données
language: fr
handle: /use_cases_4
parent: Cas d'usages
nav_order: 4

---

# Cas d'usage
## Millésimer un jeu de données


Accéder <a href="./../usecase_4_notebook.html" target="_blank">au notebook ici</a>.

La qualité de l’opendata français continue à s’améliorer d’année en année et ce
cas d’usage devient aujourd’hui rare (dans les jeux de données mis à
disposition).

Néanmoins ce cas est encore fréquent parmi les jeux de données métier (non
ouverts) historiques : parfois compilés sur plusieurs années, les codes
communes ont été saisis "à date" lors de la création d'une entité dans la base
et jamais tenus à jour.

Dans cet exemple, nous allons nous intéresser aux 
[sites pollués gérés par l'ADEME](https://data.ademe.fr/datasets/srd-ademe).


Pour en savoir plus sur les sites pollués, le lecteur est invité à consulter
[cette page](https://georisques.gouv.fr/consulter-les-dossiers-thematiques/pollutions-sols-sis-anciens-sites-industriels)
sur le site georisques.gouv.fr.

### Constituer le jeu de données

```python
import io
import os
import pandas as pd
from requests_cache import CachedSession

s = CachedSession()

url = "https://data.ademe.fr/data-fair/api/v1/datasets/srd-ademe/lines?size=10000&page=1&format=csv"

r = s.get(url)
df = pd.read_csv(io.BytesIO(r.content), sep=",", dtype=str)
```

### Corriger le jeu de données

Certains codes INSEE ont été mal formatés dans le fichier source : 
malgré la précaution de spécifier un type "str", il manque des 0 en tête de
code commune pour les neuf premiers départements français.

```python
ix = df[df.Code_INSEE.str.len() == 4].index
print(df.loc[ix, "Code_INSEE"])
df["Code_INSEE"] = df["Code_INSEE"].str.zfill(5)
print(df.loc[ix, "Code_INSEE"])
```

### Millésimer le jeu de données

```python

from french_cities import set_vintage

# =============================================================================
# Configuration de l'API INSEE
# =============================================================================
os.environ["insee_key"] = "********************"
os.environ["insee_secret"] = "********************"

# =============================================================================
# Stocker les codes initiaux pour effectuer une comparaison ultérieure
# =============================================================================
init = df["Code_INSEE"].copy()
init.name = "initial"

# =============================================================================
# Utiliser french-cities
# =============================================================================
df = set_vintage(df, 2024, "Code_INSEE")

# =============================================================================
# Comparer les résultats aux données initiales
# =============================================================================
new = df["Code_INSEE"].copy()
new.name = "final"

print((init == new).all())
ix = init[init != new].index

print(init.to_frame().join(new).loc[ix])
```
