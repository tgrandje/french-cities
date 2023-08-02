# french-cities
Boîte à outils sur les communes françaises : millésimage, reconnaissance de 
départements ou de communes...


# Installation

`pip install french-cities[full]`

Notez qu'à cette heure, `pynsee` ne supporte pas les projections de codes commune. 
Dans l'immédiat, après avoir installé `french-cities` depuis pypi, il faut donc
désinstaller `pynsee` puis réinstaller la version master courante depuis son repo 
github :
```
pip uninstall pynsee
pip install git+https://github.com/InseeFrLab/pynsee
```

L'installation "full" permet d'installer geopy qui est une dépendance 
optionnelle utilisable en dernier ressort.

# Configuration

## Ajout des clefs API INSEE
`french-cities` utilise `pynsee`, qui nécessite des cles API INSEE pour être 
fonctionnel. Jusqu'à quatre clefs peuvent être spécifiées à l'aide de variables
d'environnement :
* insee_key
* insee_secret, 
* http_proxy (le cas échéant, pour accès web derrière un proxy professionnel)
* https_proxy (le cas échéant, pour accès web derrière un proxy professionnel)

Merci de se référer à [la documentation de `pynsee`](https://pynsee.readthedocs.io/en/latest/api_subscription.html)
pour plus d'information sur les clefs API et la configuration.

A noter que la configuration des proxy par variable d'environnement sera 
fonctionnelle pour à la fois `pynsee` et `geopy`.

## Gestion des sessions web
`pynsee` et `geopy` utilisent leur propres gestionnaires de session web. 
Ainsi, les objets Session passés en argument à `french-cities` ne seront
**PAS** partagés avec `pynsee` ou `geopy`. Cela explique la possibilité de 
passer une session en argument alors même que des proxy professionnels peuvent 
être spécifiés par variables d'environnement (pour `pynsee` et `geopy`).

## Utilisation

### Pourquoi french-cities ?
Des packages et des API sont déjà disponibles pour des recherches usuelles. Par
exemple, `pynsee` utilise les API de l'INSEE pour retrouver de multiples données
(comme les départements, les régions, etc.) ; `geopy` peut également retrouver
des communes à partir de leurs noms en s'appuyant sur la BAN (Base Adresse 
Nationale) ou sur le service de géocodage Nominatim.

La différence est que `french-cities` est optimisé pour travailler avec des données
fournies sous la forme de Series ou DataFrames pandas. Ce package gérera mieux
de gros volumes de données que ne le feraient des appels multiples à des API.

### Trouver les départements
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

Pour une documentation complète sur la fonction `find_departements`, merci 
d'utiliser la commande suivante :
`help(find_departements)`.

### Trouver les codes communes
`french-cities` peut retrouver le code commune à partir de champs multiples.
Il est capable de détecter certaines erreurs simples dans les champs (jusqu'à 
une certaine limite).

Les colonnes utilisées par l'algorithme pour cette détection sont (par ordre
de priorité) :
* 'x' et 'y' (dans ce cas, un code EPSG doit être explicitement donné);
* 'postcode' et 'city'
* 'address', 'postcode' et 'city'
* 'department' et 'city'

Il est à noter que l'algorithme peu faire être source d'erreur dès lors que
la jointure spatiale (coordonnées x & y) sera sollicitée sur un millésime ancien.
Les communes impactées sont les communes restaurées ("scission"), le flux de données
spatialisées du COG servi par pynsee n'étant pas millésimé à ce jour.

La reconnaissance syntaxique (champs postcode, city, address, departement) est
basée sur la BAN (base adresse nationale). L'algorithme ne conservera pas de
résultats insuffisamment fiables, mais des erreurs peuvent subsister (elles 
seront dans ce cas cohérentes avec les résultats de la BAN).

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

### Projection de codes communes dans un millésime donné
`french-cities` peut tenter de "projeter" un dataframe dans un millésime donné,
la date initiale demeurant inconnue (voire inexistante, les cas de fichiers
"multi-millésimés" étant fréquents dans la vie réelle).

Des erreurs peuvent survenir, notamment pour les communes restaurées (dans la 
mesure où la date initiale de la donnée est inconnue ou inexistante).

Dans le cas où la date des données est connue, il peut être pertinent d'utiliser
l'API de projection mise à disposition par l'INSEE et accessible au travers de 
`pynsee`. Il convient de noter que cette utilisation peut être lente, dans la 
mesure ou chaque commune devra être testée via l'API (qui n'autorise que 
30 requêtes par minute).

En substance, l'algorithme de `french-cities` contrôle si le code commune existe
dans le millésime souhaité :
* s'il existe il sera conservé (à l'approximation précédente près qui peut donc
impacter les communes restaurées) ;
* s'il n'existe pas, le code est recherché dans des millésimes antérieurs (et
l'API de projection de l'INSEE sera mobilisée de manière ciblée).

Cet algorithme va également :
* convertir les codes des éventuels arrondissements municipaux en celui de leur
commune de rattachement;
* convertir les codes des communes associées et déléguées en celui de leur 
commune de rattachement.

```
from french_cities import set_vintage
import pandas as pd

df = pd.DataFrame(
    [
        ["07180", "Fusion"],
        ["02077", "Commune déléguée"],
        ["02564", "Commune nouvelle"],
        ["75101", "Arrondissement municipal"],
        ["59298", "Commune associée"],
        ["99999", "Code erroné"],
        ["14472", "Oudon"],
    ],
    columns=["A", "Test"],
    index=["A", "B", "C", "D", 1, 2, 3],
)
df = set_vintage(df, 2023, field="A")
print(df)
```

Pour une documentation complète sur la fonction `set_vintage`, merci 
d'utiliser la commande suivante :
`help(set_vintage)`.

## Documentation externe

`french-cities` utilise plusieurs API externes. N'hésitez pas à consulter :
* [documentation](https://adresse.data.gouv.fr/api-doc/adresse) (en Français) de l'API Adresse
* [documentation](https://public.opendatasoft.com/explore/dataset/correspondance-code-cedex-code-insee/api/?flg=fr&q=code%3D68013&lang=fr) (en Français) de l'API OpenDataSoft.
* [Politique d'usage de Nominatim](https://operations.osmfoundation.org/policies/nominatim/)

## Support
En cas de bugues, merci d'ouvrir un ticket [sur le repo](https://github.com/tgrandje/french-cities/issues).

## Auteur
Thomas GRANDJEAN (DREAL Hauts-de-France, service Information, Développement Durable et Évaluation Environnementale, pôle Promotion de la Connaissance).

## Licence
Licence Ouverte version 2.0 [etalab-2.0](https://www.etalab.gouv.fr/wp-content/uploads/2017/04/ETALAB-Licence-Ouverte-v2.0.pdf)

## État du projet
Phase de test.