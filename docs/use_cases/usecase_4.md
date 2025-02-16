---
layout: default
title: Millésimer un jeu de données
language: fr
handle: /use_cases_4
parent: Cas d'usages
nav_order: 4

---

# Cas d'usage
## Millésimer un jeu de données


Accéder <a href="https://github.com/tgrandje/french-cities/blob/main/notebooks_docs/usecase_4.ipynb" target="_blank">au notebook ici</a>.

La qualité de l’opendata français continue à s’améliorer d’année en année et ce
cas d’usage devient aujourd’hui rare (dans les jeux de données mis à
disposition).

Néanmoins ce cas est encore fréquent parmi les jeux de données métier (non
ouverts) historiques : parfois compilés sur plusieurs années, les codes
communes ont été saisis "à date" lors de la création d'une entité dans la base
et jamais tenus à jour.

Dans cet exemple, nous allons nous intéresser aux
[sites pollués gérés par l'ADEME](https://data.ademe.fr/datasets/srd-ademe).


Pour en savoir plus sur les sites pollués, le lecteur est invité à consulter
[cette page](https://georisques.gouv.fr/consulter-les-dossiers-thematiques/pollutions-sols-sis-anciens-sites-industriels)
sur le site georisques.gouv.fr.

### Dépendances utilisées dans ce projet
* requests-cache
* pandas
* french-cities
