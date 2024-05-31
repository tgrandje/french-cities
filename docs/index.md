---
layout: default
title: Accueil
language: fr
handle: /
nav_order: 1

---

# Documentation du package python `french-cities`

Ce site contient la documentation du package python `french-cities`.

## Pourquoi french-cities ?

Des packages et des API sont déjà disponibles en langage python pour des 
recherches usuelles.
Par exemple, l'excellent package `pynsee` utilise les API de l'INSEE pour 
retrouver de multiples données :
* départements, 
* régions,
* etc.

`geopy` peut également retrouver des communes à partir de leurs noms en 
s'appuyant sur la BAN (Base Adresse Nationale) ou sur le service de géocodage 
Nominatim.

`french-cities` est quant à lui optimisé pour travailler avec des données 
fournies sous la forme de Series ou DataFrames `pandas`.
Les packages pré-cités (`pynsee`, `geopy`) sont toujours utilisés et 
constituent au demeurant des dépendances importantes de `french-cities` :
le présent package peut être considéré comme une surcouche plus adaptée aux
volumes importants de données.

## Mise en cache et optimisation des algorithmes
 
Les algorithmes proposés tiennent globalement compte de la disponibilité
des différentes sources de données. Par exemple, l'API Nominatim n'autorise
pas plus d'une requête par seconde, ce qui explique que `geopy` constitue une
dépendance optionnelle permettant d'utliser Nominatim en dernier recours. 

En outre, `french-cities` s'appuie sur deux systèmes de mise en cache :
* `pynsee` gère sa mise en cache nativement ;
* et pour d'autres requêtes web (base adresse nationale, API opendatasoft sur
les codes Cedex), les requêtes sont mises en cache avec une durée d'expiration
de 30 jours grâce au module `requests-cache` (ce qui explique la création de
fichiers SQLite au droit de l'exécution des scripts) ;
* seul le requêtage de l'API Nominatim (s'appuyant sur geopy) n'est pas mis en 
cache à date.

A moins d'utiliser spécifiquement Nominatim à haute capacité (ce que les
algorithmes visent justement à prévenir), on peut donc considérer que 
`french-cities` est relativement sûr à utiliser pour des tâches automatisées
répétitives. Bien évidemment, chaque utilisateur se doit d'utiliser ce package
de manière responsable et sous son entière responsabilité : il lui revient de
contrôler finement les résultats avant de se lancer dans des automatisations à
grande échelle.

Il est également conseillé de consulter [les documentations externes](./external_doc)
des sources utilisées.