---
layout: default
title: Projection de codes communes dans un millésime donné
language: fr
handle: /project_cities_to_year
nav_order: 6

---
# Projection de codes communes dans un millésime donné

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
* convertir les codes des éventuels arrondissements municipaux en celui de 
leurs communes de rattachement;
* convertir les codes des communes associées et déléguées en celui de leurs 
communes de rattachement.

### Docstring de la fonction `set_vintage`
```
set_vintage(df: pandas.core.frame.DataFrame, year: int, field: str) -> pandas.core.frame.DataFrame
    Project (approximatively) the cities codes of a dataframe into a desired
    vintage.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing city codes
    year : int
        Year to project the dataframe's city codes into
    field : str
        Field (column) of dataframe containing the city code
    
    Returns
    -------
    pd.DataFrame
        Projected DataFrame
```

### Exemple d'utilisation basique
```python
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

