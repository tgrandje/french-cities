---
layout: default
title: Retrouver des codes communes à partir de libellés communaux et départementaux
language: fr
handle: /use_cases_3
parent: Cas d'usages
nav_order: 3

---

# Cas d'usage
## Retrouver des codes communes à partir de libellés communaux et départementaux

Accéder <a href="./../usecase_3_notebook.html" target="_blank">au notebook ici</a>.

Dans cet exemple, il s'agit de retrouver les communes ciblées par un arrêté
de reconnaissance de l'état de
[catastrophe naturelle](https://www.service-public.fr/particuliers/vosdroits/F3076).

Par exemple, nous allons nous intéresser à l'
[arrêté du 14 novembre 2023](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000048393151).

_Remarque : dans le cadre de l'exemple, nous allons récupérer cet arrêté par 
requêtage direct du site legifrance.gouv.fr. Cette méthode peut échouer, 
le site étant doté d'un captcha. Dans une situation réelle, il conviendrait
d'utiliser l'[API Legifrance](https://api.gouv.fr/les-api/DILA_api_Legifrance)
pour accéder au contenu. Néanmoins, l'accès par API complexifie largement le
code source (ce qui n'est pas l'objet du présent cas d'usage) : il a été
choisi de rester le plus concis possible._


### Dépendances utilisées dans ce projet
* requests-cache
* pandas
* lxml
* french-cities

### Constitution du jeu de données

```python

import os
import pandas as pd
from requests_cache import CachedSession


from french_cities import find_departements_from_names, find_city

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

print(df)
```

Nous avons bien obtenu un dataframe avec (notamment) deux colonnes comprenant
des libellés communaux et départementaux en plein texte.

### Complétion des données avec french-cities

```python

# =============================================================================
# Reconnaissance des départements, puis des communes
# =============================================================================
df = find_departements_from_names(df, label="Département", alias="DEP_CODE")
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
```

### Analyse du jeu de données reconstitué
```python

# =============================================================================
# Analyse des résultats
# =============================================================================

print(df[['DEP_CODE', 'insee_com']].info())

```
Nous avons (normalement) bien reconnu les 205 communes ciblées par l'arrêté.