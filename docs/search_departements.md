---
layout: default
title: Reconnaissance des départements
language: fr
handle: /search_departements
nav_order: 4

---
# Reconnaissance des départements: `find_departements`

`french-cities` peut retrouver un code département à partir de codes postaux,
de codes communes officiels (COG/INSEE) ou de libellés en toutes lettres.

## A partir des codes postaux

Travailler à partir de codes postaux entraînera l'utilisation (par ordre de priorité) :
* de l'API [base officielle des codes postaux](https://datanova.laposte.fr/datasets/laposte-hexasmal) ;
* de l'API [BAN](https://adresse.data.gouv.fr/api-doc/adresse#csv-search) (Base Adresse Nationale) ;
* de l'API d'[OpenDataSoft](https://public.opendatasoft.com/explore/dataset/correspondance-code-cedex-code-insee/api/?flg=fr&q=code%3D68013&lang=fr) sur la base des [travaux de Christian Quest](https://public.opendatasoft.com/explore/dataset/correspondance-code-cedex-code-insee/information/?flg=fr&q=code%3D68013&lang=fr)..

La première étape permet de faire matcher des codes postaux avec l'intégralité
de la base nationale officielle.

La seconde étape permet d'exploiter les algorithmes de la BAN en cas d'échec
sur la base nationale officielle (qui n'est mise à jour que 2 fois par an uniquement).

Le cas des codes Cedex n'est que partiellement géré par la BAN et la
troisième étape permet d'exploiter les travaux de Christian Quest sur ce sujet.
Il est à noter que le jeu de données n'a pas fait l'objet d'une mise à jour depuis mars 2017.

En dernier recours, une tentative est effectuée à partir des deux (ou trois pour les DOM)
premiers caractères du code postal non reconnu. Si celui-ci correspond à un département
effectif, il sera retenu.

{: .critical }
> Il n'y a pas unicité entre un code postal donné et les départements déduits.
> Par exemple, le code postal 13780 est rattaché à des communes des départements 13 **et** 83.
> Dans ce cas, il est possible de spécifier le comportement de `find_departements` à l'aide de
> l'argument `authorize_duplicates` :
> * si `authorize_duplicates=True`, les résultats seront dupliqués ;
> * si `authorize_duplicates=False` (valeur par défaut) les potentiels doublons seront éliminés,
> et aucun résultat ne sera fourni.

Exemple d'utilisation :
```python
from french_cities import find_departements
import pandas as pd

df = pd.DataFrame(
    {
        "code_postal": ["59800", "97133", "20000"],
        "code_commune": ["59350", "97701", "2A004"],
        "communes": ["Lille", "Saint-Barthélemy", "Ajaccio"],
        "deps": ["59", "977", "2A"],
        "deps_labels": ["Nord", "Saint-Barthélemy", "Corse du Sud"],
    }
)
find_departements(
    df,
    source="code_postal",
    alias="dep_A",
    type_field="postcode",
)

>>>
  code_postal code_commune          communes deps       deps_labels dep_A
0       59800        59350             Lille   59              Nord    59
1       97133        97701  Saint-Barthélemy  977  Saint-Barthélemy   977
2       20000        2A004           Ajaccio   2A      Corse du Sud    2A
```

## A partir des codes communes

Travailler à partir de codes communes officiels peut entraîner des résultats
erronés (absence de résultats) pour des données anciennes, dans le cas de
communes ayant changé de département (ce qui est relativement rare).

Ce choix est délibéré : seuls les premiers caractères des codes commune sont
utilisés pour la reconnaissance du département (algorithme rapide et qui donne
des résultats corrects pour 99% des cas), par opposition à un requêtage
systématique aux API (processus sans erreur mais long).

Il est néanmoins possible de limiter ce comportement en effectuant au préalable
une projection des codes dans un millésime donné en activant l'argument
`do_set_vintage=True` ; cette opération ralentira considérablement le calcul
des codes département.

Exemple d'utilisation :
```python
from french_cities import find_departements
import pandas as pd

df = pd.DataFrame(
    {
        "code_postal": ["59800", "97133", "20000"],
        "code_commune": ["59350", "97701", "2A004"],
        "communes": ["Lille", "Saint-Barthélémy", "Ajaccio"],
        "deps": ["59", "977", "2A"],
        "deps_labels": ["Nord", "Saint-Barthélemy", "Corse du Sud"],
    }
)
df = find_departements(
    df,
    source="code_commune",
    alias="dep_B",
    type_field="insee",
    do_set_vintage=True,
)
```

## A partir des libellés communaux

Dans ce cas, `french-cities` exécute un simple fuzzy-matching assorti d'un filtre
sur score minimal.

Exemple d'utilisation :
```python
from french_cities import find_departements
import pandas as pd

df = pd.DataFrame(
    {
        "code_postal": ["59800", "97133", "20000"],
        "code_commune": ["59350", "97701", "2A004"],
        "communes": ["Lille", "Saint-Barthélémy", "Ajaccio"],
        "deps": ["59", "977", "2A"],
        "deps_labels": ["Nord", "Saint-Barthélemy", "Corse du Sud"],
    }
)
df = find_departements(
    df,
    source="deps_labels",
    alias="dep_C",
    type_field="label",
)
```

## Docstring de la fonction `find_departements`
```
find_departements(
    df: pandas.DataFrame,
    source: str,
    alias: str,
    type_field: str,
    session: requests.Session = None,
    authorize_duplicates: bool = False,
    do_set_vintage: bool = True
) -> pandas.DataFrame:

    Compute departement's codes from postal, official codes (ie. INSEE COG)
    or labels in full text.
    Adds the result as a new column to dataframe under the label 'alias'.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing official cities codes
    source : str
        Field containing the post codes, official codes or labels
    alias : str
        Column to store the departements' codes unto
    type_field : str
        Type of codes passed under `alias` label. Should be either 'insee' for
        official codes, 'postcode' for postal codes or 'label' for labels.
    session : Session, optional
        Web session. The default is None (and will use a CachedSession with
        30 days expiration)
    authorize_duplicates : bool, optional
        If True, authorize duplication of results when multiple results are
        acceptable for a given postcode (for instance, 13780 can result to
        either 13 or 83 ). If False, duplicates will be removed, hence no
        result will be available. False by default.
    do_set_vintage : bool, optional
        If True, set a vintage projection for df. If False, don't bother (will
        be faster). Should be False when df was already computed from a given
        function out of pynsee or french-cities. Should be True when used on
        almost any other dataset.
        The default is True.

    Raises
    ------
    ValueError
        If type_field not among "postcode", "insee", "labels".

    Returns
    -------
    df : pd.DataFrame
        Updated DataFrame with departement's codes
```
