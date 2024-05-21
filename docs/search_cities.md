---
layout: default
title: Reconnaissance des communes
language: fr
handle: /search_cities
nav_order: 5

---
# Reconnaissance des communes

`french-cities` peut retrouver un code commune à partir de champs multiples.
Il est capable de détecter certaines erreurs simples dans les champs (jusqu'à 
une certaine limite).

Les colonnes utilisées par l'algorithme pour cette détection sont (par ordre
de priorité) :
* coordonnées 'x' et 'y' (dans ce cas, un code EPSG doit être explicitement donné);
* 'postcode' et 'city'
* 'address', 'postcode' et 'city'
* 'department' et 'city'

Il est à noter que l'algorithme peu faire être source d'erreur dès lors que
la jointure spatiale (coordonnées x & y) sera sollicitée sur un millésime ancien.
Les communes impactées sont les communes restaurées ("scission"), le flux de données
spatialisées du COG servi par `pynsee` n'étant pas millésimé à ce jour.

La reconnaissance syntaxique (champs postcode, city, address, departement) est
basée sur un fuzzy matching en langage python, l'API BAN (base adresse nationale),
ou l'API Nominatim d'OSM (si activé). 
L'algorithme ne conservera pas de résultats insuffisamment fiables, mais des 
erreurs peuvent subsister.

```
from french_cities import find_city
import pandas as pd

df = pd.DataFrame(
    [
        {
            "x": 2.294694,
            "y": 48.858093,
            "location": "Tour Eiffel",
            "dep": "75",
            "city": "Paris",
            "address": "5 Avenue Anatole France",
            "postcode": "75007",
            "target": "75056",
        },
        {
            "x": 8.738962,
            "y": 41.919216,
            "location": "mairie",
            "dep": "2A",
            "city": "Ajaccio",
            "address": "Antoine Sérafini",
            "postcode": "20000",
            "target": "2A004",
        },
        {
            "x": -52.334990,
            "y": 4.938194,
            "location": "mairie",
            "dep": "973",
            "city": "Cayenne",
            "address": "1 rue de Rémire",
            "postcode": "97300",
            "target": "97302",
        },
        {
            "x": np.nan,
            "y": np.nan,
            "location": "Erreur code postal Lille/Lyon",
            "dep": "59",
            "city": "Lille",
            "address": "1 rue Faidherbe",
            "postcode": "69000",
            "target": "59350",
        },
    ]
)
df = find_city(df, epsg=4326)

print(df)
```

Pour une documentation complète sur la fonction `find_city`, merci 
d'utiliser la commande suivante :
`help(find_city)`.

**Nota** : pour activer l'utilisation de `geopy` (API Nominatim d'OpenStreeMap) 
en dernier ressort, il convient d'utiliser l'argument `use_nominatim_backend=True`.