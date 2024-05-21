---
layout: default
title: Reconnaissance des départements
language: fr
handle: /search_departements
nav_order: 4

---
# Reconnaissance des départements

`french-cities` peut retrouver un code département à partir de codes postaux ou 
de codes communes officiels (COG/INSEE).

Travailler à partir de codes postaux entraînera l'utilisation de la BAN (Base
Adresse Nationale) et devrait fournir des résultats corrects. Le cas des codes
Cedex n'étant que partiellement géré par la BAN, un appel est fait dans un
second temps à l'[API d'OpenDataSoft](https://public.opendatasoft.com/explore/dataset/correspondance-code-cedex-code-insee/api/?flg=fr&q=code%3D68013&lang=fr)
construite sur la base des [travaux de Christian Quest](https://public.opendatasoft.com/explore/dataset/correspondance-code-cedex-code-insee/information/?flg=fr&q=code%3D68013&lang=fr).
Cette utilisation s'appuie sur un accès freemium non authentifié; l'utilisateur 
du package est invité à contrôler les conditions générales d'utilisation de l'API auprès du
fournisseur.

Travailler à partir de codes communes officiels peut entraîner des résultats
erronés pour des données anciennes, dans le cas de communes ayant changé de
département (ce qui est relativement rare).
Ce choix est délibéré : seuls les premiers caractères des codes commune sont
utilisés pour la reconnaissance du département (algorithme rapide et qui donne
des résultats corrects pour 99% des cas), par opposition à un requêtage
systématique aux API (processus sans erreur mais long).

```
from french_cities import find_departements
import pandas as pd

df = pd.DataFrame(
    {
        "code_postal": ["59800", "97133", "20000"],
        "code_commune": ["59350", "97701", "2A004"],
        "communes": ["Lille", "Saint-Barthélémy", "Ajaccio"],
        "deps": ["59", "977", "2A"],
    }
)
df = find_departements(df, source="code_postal", alias="dep_A", type_code="postcode")
df = find_departements(df, source="code_commune", alias="dep_B", type_code="insee")

print(df)
```

On peut également travailler directement à partir des noms de départements,
en utilisant à la place la fonction `find_departements_from_names` :

```
from french_cities import find_departements_from_names
import pandas as pd

df = pd.DataFrame(
    {
        "deps": ["Corse sud", "Alpe de Haute-Provence", "Aisne", "Ain"],
    }
)
df = find_departements_from_names(df, label="deps")

print(df)
```

Pour une documentation complète sur les fonctions `find_departements` ou
`find_departements_from_names`, merci d'utiliser les commandes suivantes : 
`help(find_departements)` ou `help(find_departements_from_names)`.