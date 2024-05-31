---
layout: default
title: Reconnaissance des départements
language: fr
handle: /search_departements
nav_order: 4

---
# Reconnaissance des départements

## A partir de codes communes ou codes postaux : `find_departements`

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

### Docstring de la fonction `find_departements`
```
find_departements(df: pandas.core.frame.DataFrame, source: str, alias: str, type_code: str, session: requests.sessions.Session = None) -> pandas.core.frame.DataFrame
    Compute departement's codes from postal or official codes (ie. INSEE COG)'
    Adds the result as a new column to dataframe under the label 'alias'.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing official cities codes
    source : str
        Field containing the post or official codes
    alias : str
        Column to store the departements' codes unto
    type_code : str
        Type of codes passed under `alias` label. Should be either 'insee' for
        official codes or 'postcode' for postal codes.
    session : Session, optional
        Web session. The default is None (and will use a CachedSession with
        30 days expiration)
    
    Raises
    ------
    ValueError
        If type_code not among "postcode", "insee".
    
    Returns
    -------
    df : pd.DataFrame
        Updated DataFrame with departement's codes
```

### Exemples d'utilisation basiques

```python
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

## A partir de noms de départements : `find_departements_from_names`

On peut également travailler directement à partir des noms de départements,
en utilisant à la place la fonction `find_departements_from_names`.

### Docstring de la fonction `find_departements_from_names`
```
find_departements_from_names(df: pandas.core.frame.DataFrame, label: str, alias: str = 'DEP_CODE') -> pandas.core.frame.DataFrame
    Retrieve departement's codes from their names.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing official departement's names
    label : str
        Field containing the label of the departements
    alias : str, optional
        Column to store the departements' codes unto.
        Default is "DEP_CODE"
    
    Returns
    -------
    df : pd.DataFrame
        Updated DataFrame with departement's codes
```

### Exemple d'utilisation basique

```python
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