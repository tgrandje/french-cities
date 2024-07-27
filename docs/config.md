---
layout: default
title: Configuration
language: fr
handle: /config
nav_order: 3

---
# Configuration

## Ajout des clefs API INSEE

`french-cities` utilise `pynsee`, qui nécessite des cles API INSEE pour être
fonctionnel. Deux variables d'environnement doivent impérativement être spécifiées :

* insee_key
* insee_secret

Merci de se référer à 
[la documentation de `pynsee`](https://pynsee.readthedocs.io/en/latest/api_subscription.html)
pour plus d'information sur les clefs API et la configuration.

Pour mémoire, il est tout à fait possible de fixer des variables d'environnement
depuis un environnement python, à l'aide des instructions suivantes :

```python
import os
os.environ["insee_key"] = "ma-clef-applicative"
os.environ["insee_secret"] = "ma-clef-secrete"
```
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
