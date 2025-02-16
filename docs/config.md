---
layout: default
title: Configuration
language: fr
handle: /config
nav_order: 3

---
# Configuration

## Ajout des clefs API INSEE

`french-cities` utilise `pynsee`. Depuis la version 0.2.0 de `pynsee` et 1.1.0 de `french-cities`,
plus aucune clef API n'est nécessaire.

{: .warning }
Comme `pynsee` est un outil beaucoup plus riche qui ne se limite pas à récupérer des
informations communales, il affichera par défaut des alertes (absence de clef API SIRENE notamment).
Ces alertes devraient normalement être masquées par `french-cities` : si ce n'était pas le
cas, merci d'ouvrir une issue.

## Configuration des proxies

Les requêtes web fournies `french-cities` sont de trois types :
* celles générées par `pynsee`, interrogeant les API INSEE ;
* celles générées par `geopy`, interrogeant l'API Nominatim ;
* celles générées en propre par `french-cities` pour interroger l'API de la
Base Adresse Nationale et l'API Base officielle des codes postaux.

Dans le cas où l'on souhaiterait utiliser des proxies professionnels
pour connexion internet, il suffit de fixer deux variables d'environnement
supplémentaires :

* http_proxy
* https_proxy

Néanmoins, si l'utilisateur souhaite configurer son propre objet session
et le fournir en argument optionnel à `french-cities`, il lui revient :
* de fixer par lui-même le(s) proxy(ies) attachés à sa session ;
* de continuer à fixer les variables d'environnement `https_proxy` et
`http_proxy` (utilisées en propre par `pynsee` et `geopy` qui utilisent
leurs propres objets session).

Pour mémoire, il est tout à fait possible de fixer des variables d'environnement
depuis un environnement python, à l'aide des instructions suivantes :

```python
import os
os.environ["insee_key"] = "ma-clef-applicative"
os.environ["insee_secret"] = "ma-clef-secrete"
```

On peut également utiliser des packages comme `python-dotenv` pour travailler
à partir de fichier .env.
