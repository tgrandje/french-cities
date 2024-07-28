---
layout: default
title: Combler des données communales manquantes
language: fr
handle: /use_cases_1
parent: Cas d'usages
nav_order: 1

---

# Cas d'usage

## Combler des données communales manquantes à partir de libellés, codes postaux, adresses et coordonnées géographiques

Accéder <a href="https://github.com/tgrandje/french-cities/blob/main/notebooks_docs/usecase_1.ipynb" target="_blank">au notebook ici</a>.

Dans cet exemple, il s'agit de compléter les données communales d'un jeu plutôt
bien renseigné, mais incomplet. On s'intéresse à l'exemple des données
produites par l'
[API Géorisques Installations Classées](https://georisques.gouv.fr/doc-api#/Installations%20Class%C3%A9es/rechercherAiotsParGeolocalisation).

Pour en savoir plus sur les installations classées, vous pouvez consulter
[cette page](https://www.georisques.gouv.fr/consulter-les-dossiers-thematiques/installations).

### Dépendances utilisées dans ce projet
* requests-cache
* pandas
* tqdm
* french-cities
