# french-cities
Toolbox on french cities: set vintage, find departments, find cities...

# Documentation

A full documentation with usecases is available at [https://tgrandje.github.io/french-cities/](https://tgrandje.github.io/french-cities/).
Obviously, it is only available in french as yet.
Any help is welcome to build a multi-lingual documentation website.

Until then, a basic english documentation will stay available in the present README. 

# Installation

`pip install french-cities[full]`

Note that the "full" installation will also install geopy, which might use
Nominatim API for city recognition as a last resort.

# Configuration

## Setting INSEE's API keys
`french-cities` uses `pynsee` under the hood. For it to work, you need to set
the credentials up. You can set up to four environment variables:
* insee_key
* insee_secret, 
* http_proxy (if accessing web behind a corporate proxy)
* https_proxy (if accessing web behind a corporate proxy)

Please refer to [`pynsee`'s documentation](https://pynsee.readthedocs.io/en/latest/api_subscription.html)
to help configure the API's access.

Note that setting environment variable for proxy will set it for both `pynsee`
and `geopy`.

## Session management
Note that `pynsee` and `geopy` use their own web session. Every Session object 
you will pass to `french-cities` will **NOT** be shared with `pynsee` or `geopy`. 
This explains the possibility to pass a session as an argument to `french-cities` 
functions, even if you had to configure the corporate proxy through environment 
variables for `pynsee` and `geopy`.

## Basic usage

### Why french-cities?
There are already available packages and APIs meant to be used for basic french
cities management. For instance, `pynsee` uses the INSEE's API to retrieve
multiple data (including departement, region, ...). `geopy` can also retrieve
cities from their names using the BAN (Base Adresse Nationale) API or the 
Nominatim geocoding service.

The difference is that `french-cities` is primarly meant to perform against whole
pandas series/dataframes. It should handle better performance than multiple API 
calls and will optimize the call to each endpoints.

### Retrieve departements' codes
`french-cities` can retrieve departement's codes from postal codes or official
(COG/INSEE) codes. 

Working from postal codes will make use of the BAN (Base Adresse Nationale)
and should return correct results. The case of "Cedex" codes is only partially
covered by the BAN, so [OpenDataSoft's API](https://public.opendatasoft.com/explore/dataset/correspondance-code-cedex-code-insee/api/?flg=fr&q=code%3D68013&lang=fr),
constructed upon [Christian Quest works](https://public.opendatasoft.com/explore/dataset/correspondance-code-cedex-code-insee/information/?flg=fr&q=code%3D68013&lang=fr).
This consumes the freemium API and no authentication is included:
the user of the present package should check the current API's legal terms
directly on OpenDataSoft's website.

Working from official codes may give wrong results when working on an old
dataset and with cities which have changed of departments (which is rarely seen). 
This is deliberate: it will use the first characters of the cities' codes 
(which is a fast process and 99% accurate) instead of using an API (which is
lengthy though foolproof).

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

One can also work directly from departement's names, using 
`find_departements_from_names` instead :

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

For a complete documentation on `find_departements` or 
`find_departements_from_names`, please type `help(find_departements)` or
`help(find_departements_from_names)`.

### Retrieve cities' codes
`french-cities` can retrieve cities' codes from multiple fields. It will work
out basic mistakes (up to a certain limit).

The columns used by the algorithm can be (in the order of precedence used by
the algorithm):
* 'x' and 'y' (in that case, epsg must be explicitly given);
* 'postcode' and 'city'
* 'address', 'postcode' and 'city'
* 'department' and 'city'

Note that the algorithm can (and will) make errors using xy coordinates on a 
older vintage (ie different from the current one) in the case of historic 
splitting of cities (the geographic files are not vintaged yet).

The lexical (postcode, city, address, departement) recognition is based on a
python fuzzy matching, the BAN API(base adresse nationale) or the Nominatim
API of OSM (if activated). The algorithm won't collect underscored
results, but failures may still occure.

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

For a complete documentation on `find_city`, please type 
`help(find_city)`.

**Note** : to activate `geopy` (Nominatim API from OpenStreeMap) usage in last 
resort, you will need to use the argument `use_nominatim_backend=True`.

### Set vintage to cities' codes
`french-cities` can try to project a given dataframe into a set vintage,
starting from an unknown vintage (or even a non-vintaged dataset, which is 
often the case).

Error may occur for splitted cities as the starting vintage is unknown
(or inexistant).

In case of a known starting vintage, you can make use of
INSEE's projection API (with `pynsee`). Note that this might prove slower as
each row will have to induce a request to the API (which allows up to 
30 requests/minute).

Basically, the algorithm of `french-cities` will try to see if a given city
code exists in the desired vintage:
* if yes, it will be kept (we the aforementionned approximation regarding
restored cities);
* if not, it will look in older vintages and make use of INSEE's projection API.

This algorithm will also:
* convert communal districts' into cities' codes;
* convert delegated or associated cities' codes into it's parent's.

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

For a complete documentation on `set_vintage`, please type 
`help(set_vintage)`.

## External documentation

`french-cities` makes use of multiple APIs. Please read :
* [documentation](https://adresse.data.gouv.fr/api-doc/adresse) (in french) on API Adresse
* [documentation](https://public.opendatasoft.com/explore/dataset/correspondance-code-cedex-code-insee/api/?flg=fr&q=code%3D68013&lang=fr) (in french) on OpenDataSoft API
* [Nominatim Usage Policy](https://operations.osmfoundation.org/policies/nominatim/)

## Support

In case of bugs, please open an issue [on the repo](https://github.com/tgrandje/french-cities/issues).

## Contribution
Any help is welcome.

## Author
Thomas GRANDJEAN (DREAL Hauts-de-France, service Information, Développement Durable et Évaluation Environnementale, pôle Promotion de la Connaissance).

## Licence
GPL-3.0-or-later

## Project Status
In production.