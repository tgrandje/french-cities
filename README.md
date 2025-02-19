# french-cities

![PyPI - Version](https://img.shields.io/pypi/v/french-cities)
[![Supported Python Versions](https://img.shields.io/pypi/pyversions/french-cities)](https://pypi.python.org/pypi/french-cities/)

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
![flake8 checks](https://raw.githubusercontent.com/tgrandje/french-cities/refs/heads/main/badges/flake8-badge.svg)
![Test Coverage](https://raw.githubusercontent.com/tgrandje/french-cities/refs/heads/main/badges/coverage-badge.svg)

![GitHub Issues or Pull Requests](https://img.shields.io/github/issues/tgrandje/french-cities)
![GitHub commits since latest release](https://img.shields.io/github/commits-since/tgrandje/french-cities/latest)

![Monthly Downloads](https://img.shields.io/pypi/dm/french-cities)
![Total Downloads](https://img.shields.io/pepy/dt/french-cities)
![Conda Downloads](https://img.shields.io/conda/d/conda-forge/french-cities)


This repo contains the documentation of the python french-cities package, a
package aimed at improving the referencing of municipalities in French 🇫🇷
datasets.

# Documentation

A full documentation with usecases is available at
[https://tgrandje.github.io/french-cities/](https://tgrandje.github.io/french-cities/).
Obviously, it is only available in french as yet.
Any help is welcome to build a multi-lingual documentation website.

Until then, a basic english documentation will stay available in the present README.

# Why french-cities?

Do you have any data:
* which municipal locations are provided through approximate addresses, or via geographical 🗺️ coordinates?
* which municipalities are referenced by their postal codes and their labels 😮?
* which departments are written in full text 🔡?
* which spelling are dubious (for instance, torturing the _<del>Loire</del> Loir-et-Cher_) or obsolete
(for instance, referencing _Templeuve_, a city renamed as _Templeuve-en-Pévèle_ since 2015)?
* or compiled over the years and where cities' codes are a patchwork of multiple 🤯 vintages?

**Then 'french-cities' is for you 🫵!**

# Installation

## pip

`pip install french-cities`

## conda

See [french-cities' feedstock](https://github.com/conda-forge/french-cities-feedstock?tab=readme-ov-file#installing-french-cities).

# Configuration

## Setting INSEE's API keys
`french-cities` uses `pynsee` under the hood. Starting from `pynsee 0.2.0` (and `french-cities 1.1.0`),
an API key is **not necessary anymore**.

Note that as `pynsee` is far more than just retrieving information on cities:
by default, it will alert you on missing SIRENE API keys.
`french-cities` *should* silence those alerts (as they are not relevant to
the present usecases). If those alerts popup, please get in touch.

## Working behind a corporate proxy

Please set those (usual) environment variables to allow working behind a proxy:
* http_proxy (if accessing web behind a corporate proxy)
* https_proxy (if accessing web behind a corporate proxy)

If you can't set those variables directly, you can either have a look at python-dotenv
or set those directly using python:

```python
import os
os.environ["https_proxy"] = "http://my_proxy_server:port"
os.environ["http_proxy"] = "http://my_proxy_server:port"
```

## Session management
Note that `pynsee` and `geopy` (both used under the hood) use their own web session.
Every Session object you will pass to `french-cities` will neither be shared with
`pynsee` nor `geopy`.

This explains the possibility to pass a session as an argument to `french-cities`
functions, even if you had to configure the corporate proxy through environment
variables (those will also impact `pynsee` and `geopy`).

## Basic usage

### Retrieve departements' codes
`french-cities` can retrieve departement's codes from postal codes, official
(COG/INSEE) codes or labels.

Working from postal codes will make use of the BAN (Base Adresse Nationale)
and should return correct results. The case of "Cedex" codes is only partially
covered by the BAN, so [OpenDataSoft's API](https://public.opendatasoft.com/explore/dataset/correspondance-code-cedex-code-insee/api/?flg=fr&q=code%3D68013&lang=fr),
constructed upon [Christian Quest works](https://public.opendatasoft.com/explore/dataset/correspondance-code-cedex-code-insee/information/?flg=fr&q=code%3D68013&lang=fr).
This consumes the freemium API and no authentication is included:
the user of the present package should check the current API's legal terms
directly on OpenDataSoft's website.

Working from official codes may sometime give empty results (when working on an old
dataset and with cities which have changed of departments, which is rarely seen).
This is deliberate: it will mostly use the first characters of the cities' codes
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
df = find_departements(df, source="code_postal", alias="dep_A", type_field="postcode")
df = find_departements(df, source="code_commune", alias="dep_B", type_field="insee")
df = find_departements(df, source="communes", alias="dep_C", type_field="label")

print(df)
```

For a complete documentation on `find_departements`, please type `help(find_departements)`.

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
Any help is welcome. Please refer to the [CONTRIBUTING file](https://github.com/tgrandje/french-cities/blob/main/CONTRIBUTING.md).

## Author
Thomas GRANDJEAN (DREAL Hauts-de-France, service Information, Développement Durable et Évaluation Environnementale, pôle Promotion de la Connaissance).

## Licence
[GPL-3.0-or-later](https://github.com/tgrandje/french-cities/blob/main/LICENSE.md)

## Project Status
Stable.
