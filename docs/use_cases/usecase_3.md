---
layout: default
title: Retrouver des codes communes à partir de libellés communaux et départementaux
language: fr
handle: /use_cases_3
parent: Cas d'usages
nav_order: 3

---

# Cas d'usage
## Retrouver des codes communes à partir de libellés communaux et départementaux

Accéder <a href="https://github.com/tgrandje/french-cities/blob/main/notebooks_docs/usecase_3.ipynb" target="_blank">au notebook ici</a>.

Dans cet exemple, il s'agit de retrouver les communes ciblées par un arrêté
de reconnaissance de l'état de
[catastrophe naturelle](https://www.service-public.fr/particuliers/vosdroits/F3076).

Par exemple, nous allons nous intéresser à l'
[arrêté du 14 novembre 2023](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000048393151).

_Remarque : dans le cadre de l'exemple, nous allons récupérer cet arrêté par
requêtage direct du site legifrance.gouv.fr. Cette méthode peut échouer,
le site étant doté d'un captcha. Dans une situation réelle, il conviendrait
d'utiliser l'[API Legifrance](https://api.gouv.fr/les-api/DILA_api_Legifrance)
pour accéder au contenu. Néanmoins, l'accès par API complexifie largement le
code source (ce qui n'est pas l'objet du présent cas d'usage) : il a été
choisi de rester le plus concis possible._


### Dépendances utilisées dans ce projet
* requests-cache
* pandas
* lxml
* french-cities
* matplotlib (facultatif)
* geopandas (facultatif)
