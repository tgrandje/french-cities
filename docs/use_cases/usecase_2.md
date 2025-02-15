---
layout: default
title: Retrouver des codes communes à partir de codes postaux et libellés
language: fr
handle: /use_cases_2
parent: Cas d'usages
nav_order: 2

---

# Cas d'usage
## Retrouver des codes communes à partir de codes postaux et libellés de communes

Accéder <a href="https://github.com/tgrandje/french-cities/blob/main/notebooks_docs/usecase_2.ipynb" target="_blank">au notebook ici</a>.

La qualité de l'opendata français continue à s'améliorer d'année en année et ce
cas d'usage devient aujourd'hui rare.
Ceci étant dit, on trouve toujours des jeux de données  (parfois historiques)
pour lesquels sont fournis des codes postaux et des libellés communaux (au lieu
de codes INSEE).

Dans cet exemple, on s'intéressera aux marchés publics conclus recensés sur la
plateforme des achats de l’Etat en 2015. Le jeu de données peut être retrouvé
[sur data.gouv.fr](https://www.data.gouv.fr/fr/datasets/marches-publics-conclus-recenses-sur-la-plateforme-des-achats-de-letat/)

### Dépendances utilisées dans ce projet
* openpyxl
* numpy
* pandas
* requests-cache
* french-cities
* matplotlib (facultatif)
* seaborn (facultatif)
