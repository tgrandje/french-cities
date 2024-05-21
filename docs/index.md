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

Des packages et des API sont déjà disponibles en langage python pour des recherches usuelles.
Par exemple, l'excellent package `pynsee` utilise les API de l'INSEE pour retrouver de multiples données :
* départements, 
* régions,
* etc.

`geopy` peut également retrouver des communes à partir de leurs noms en s'appuyant sur la BAN (Base Adresse Nationale) ou sur le service de géocodage Nominatim.

`french-cities` est quant à lui optimisé pour travailler avec des données fournies sous la forme de Series ou DataFrames `pandas`.
Les packages pré-cités (`pynsee`, `geopy`) sont toujours utilisés et constituent au demeurant des dépendances importantes de `french-cities` :
le présent package peut être considéré comme une surcouche plus adaptée aux volumes importants de données.