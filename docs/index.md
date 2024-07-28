---
layout: default
title: Accueil
language: fr
handle: /
nav_order: 1

---

# Documentation du package python `french-cities`

Ce site contient la documentation du package python `french-cities`,
un package visant à améliorer le référencement des communes dans les jeux
de données français 🇫🇷.

## Pourquoi french-cities ?

Avez-vous des données :
* dont la localisation communale est fournie par le biais d'adresses 
approximatives, ou via des coordonnées géographiques 🗺️ ?
* dont les communes sont référencées par leurs codes postaux et 
leurs libellés 😮 ? 
* dont les départements sont écrits en toutes lettres 🔡 ?
* dont les libellés sont douteux (torturant par exemple 
le _<del>Loire</del> Loir-et-Cher_) ou obsolètes (mentionnant
par exemple _Templeuve_, une commune renommée en 
 _Templeuve-en-Pévèle_ depuis 2015) 🤦‍♂️ ?
* ou compilées au fil des années et dont les codes communes
constituent un patchwork de millésimes différents 🤯 ?

**Alors `french-cities` est fait pour vous 🫵 !**

## Contexte

Ce projet est né des besoins de la 
[DREAL Hauts-de-France](https://www.hauts-de-france.developpement-durable.gouv.fr/) 
pour la consolidation de jeux de données (opendata ou internes) 📊.
Et curieusement, nous n'avons pas trouvé de solution sur étagère
répondant à ce besoin.

Nous avons alors construit, amélioré et maintenu notre propre algorithme.
Aujourd'hui, une nouvelle étape a été franchie avec la publication et
l'ouverture 🔓 de cet algorithme dans un package python.

Ce package s'appuie bien sûr sur des librairies déjà existantes.
Car si aucune réponse globale au problème n'a été trouvée, 
de nombreuses solutions *partielles* ont été identifiées. La plus-value
de `french-cities` tient justement dans l'articulation de ces
solutions et à leur optimisation pour répondre aux cas d'usage.

Par exemple, les API de l'INSEE permettent de réaliser des projections
d'un code commune vers un millésime donné. L'excellente implémentation
en python du package `pynsee` le permet effectivement.
Oui, mais voilà, pour 
exécuter une projection, il faut connaître la date de départ, ce qui
est souvent une gageure 🕵️. En outre, la consommation des API de l'INSEE
est plafonnée à 30 requêtes par minute, ce qui pour un petit jeu
de données de 1000 lignes nous emmène déjà à plus de 30 minutes
d'exécution ⌛.

D'un autre côté, l'API Base Adresse Nationale (BAN) a déjà été
intégrée dans le package `geopy`, au côté d'autres geocodeurs 🌍 comme
le moteur de recherche OpenStreetMap Nominatim.
Mais là aussi, l'exercice ne tient pas la charge d'un jeu de données
un tant soit peu volumineux : `geopy` exécute des requêtes individuelles
à la BAN (limitées à 50 appels par seconde) alors qu'elle dispose 
d'un point d'entrée CSV. Pour un jeu de données conséquent de 100 000 lignes, 
cela nous amène tout de même à 30 minutes de temps de traitement.
Quant à Nominatim, les conditions générales d'utilisation limitent 
sa consommation au rythme de 30 requêtes par minute ⌛.

En outre, si `pynsee` dispose d'un cache pour les jeux de données
nationaux, ce n'est pas totalement le cas pour les projections de millésime.
Ce n'est pas non plus le cas de `geopy` (alors même qu'il s'agit d'une
recommandation forte de Nominatim, même pour un usage raisonné).

`french-cities` a quant à lui été optimisé pour travailler avec des
jeux de données volumineux (sans avoir la prétention d'être le plus
efficace pour de petits datasets)[^1]. A cet effet, il
travaille essentiellement à partir de Series ou DataFrames `pandas` 🐼.

[^1]:A titre d'exemple, les utilisations publiées dans la présente
    documentation s'appuient sur le traitement de jeux de données
    entre 200 et 12000 lignes ; des tests sur des jeux de données à plus de 
    1 million de lignes ont également été effectués.

Les premières utilisations vous sembleront particulièrement lentes,
mais le système de mise en cache devrait permettre des résultats
plus rapides lors d'utilisation ultérieures.
En particulier, l'optimisation du cache permet à `french-cities`
d'être parfaitement adapté à une utilisation
dans des tâches automatisées 🕙.

Nous vous invitons aussi à consulter [les documentations externes](./external_doc)
des sources utilisées.

## Bugues

Aucun package n'est parfait, et sûrement pas du premier coup.
Si vous détectez des bugues, vous êtes invités à nous les partager
sur [le guichet](https://github.com/tgrandje/french-cities/issues)
du projet.