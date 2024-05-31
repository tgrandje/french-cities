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
L'algorithme ne conservera pas les résultats insuffisamment fiables, mais des 
erreurs peuvent bien sûr subsister.

### Docstring de la fonction `find_city`

```
find_city(df: pandas.core.frame.DataFrame, year: str = 'last', x: Union[str, bool] = 'x', y: Union[str, bool] = 'y', dep: Union[str, bool] = 'dep', city: Union[str, bool] = 'city', address: Union[str, bool] = 'address', postcode: Union[str, bool] = 'postcode', field_output: str = 'insee_com', epsg: int = None, session: requests.sessions.Session = None, use_nominatim_backend: bool = False) -> pandas.core.frame.DataFrame
    Find cities in a dataframe using multiple methods (either based on
    valid geolocation or lexical fields).
    
    Do note that the results based on geolocation will be approximative as the
    IGN's WFS data is not vintaged (yet ?). The spatial join will then be
    computed against latest available data. A reprojection in the desired
    vintage will be done afterwards, but cities joined during this lapse time
    will NOT be correctly found.
    
    Nonetheless, recognition based on lexical fields is also unperfect. These
    will use the Base Adresse Nationale (BAN) API, but results can't be
    guaranteed. The results using geolocation will then be given precedence.
    
    To activate geolocation recognition, 2 criteria must be satisfied:
        - valids x and y fields (which exact labels will be passed as x and y
          arguments)
        - valid EPSG code related to the current projection
    
    Lexical recognition will try to use the following fields (in that order
    of precedence):
        - department + city label (fuzzy matching through python)
        - postcode + city label (through the BAN)
        - address + postcode + city label (through the BAN)
        - department + city label (through the BAN)
        - postcode + city label (through Nominatim, if activated)
        - dep + city label (through Nominatim, if activated)
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame onto which city recognition should be perfomed
    year : str, optional
        Desired vintage for cities. year should be of a type castable to int or
        'last'. The default is "last".
    x : str, optional
        Field (column) containing the x coordinates values. Set to False if
        not available. The default is "x".
    y : str, optional
        Field (column) containing the y coordinates values. Set to False if
        not available. The default is "y".
    dep : str, optional
        Field (column) containing the department values. Set to False if
        not available. The default is "dep".
    city : str, optional
        Field (column) containing the city label values. Set to False if
        not available. The default is "city".
    address : str, optional
        Field (column) containing the addresses values. Set to False if
        not available. The default is "address".
    postcode : str, optional
        Field (column) containing the post office codes values. Set to False if
        not available. The default is "postcode".
    field_output : str, optional
        Column to store the cities code into. The default is "insee_com".
    epsg : int, optional
        EPSG code of projection. The default is None.
    session : Session, optional
        Requests Session to use for web queries to APIs. Note that pynsee
        (used under the hood for geolocation recognition) uses it's own
        session. The default is None (and will use a CachedSession with
        30 days expiration)
    use_nominatim_backend : bool, optional
        If set to True, will try to use the Nominatim API in last resort. This
        might slow the process as the API's rate is on one request per second.
        Please read Nominatim Usage Policy at
        https://operations.osmfoundation.org/policies/nominatim/
    
    Raises
    ------
    ValueError
        If year is not castable to int or equals to "last", or if no columns
        have been found which will match either (x, y), (postcode, city), or
        (dep, city)
    
    Returns
    -------
    pd.DataFrame
        Initial dataframe with a new column containing cities' codes (labelled
        according to `field_output` value.)
```

### Exemple d'utilisation basique

```python

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