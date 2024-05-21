---
layout: default
title: Configuration
language: fr
handle: /config
nav_order: 3

---
# Configuration

## Ajout des clefs API INSEE

`french-cities` utilise `pynsee`, qui nécessite des cles API INSEE pour être fonctionnel. Jusqu'à quatre clefs peuvent être spécifiées à l'aide de variables d'environnement :

* insee_key
* insee_secret,
* http_proxy (le cas échéant, pour accès web derrière un proxy professionnel)
* https_proxy (le cas échéant, pour accès web derrière un proxy professionnel)

Merci de se référer à [la documentation de `pynsee`](https://pynsee.readthedocs.io/en/latest/api_subscription.html) pour plus d'information sur les clefs API et la configuration.

A noter que la configuration des proxy par variable d'environnement sera fonctionnelle pour à la fois pynsee et geopy.

## Gestion des sessions web
`pynsee` et `geopy` utilisent leur propres gestionnaires de session web.
Ainsi, les objets `Session` passés en argument à french-cities ne seront **PAS** partagés avec `pynsee` ou `geopy`.
Cela explique la possibilité de passer une session en argument alors même que des proxy professionnels peuvent être spécifiés par variables d'environnement (pour `pynsee` et `geopy`).