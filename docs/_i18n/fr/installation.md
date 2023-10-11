# Installation

`pip install french-cities[full]`

Notez qu'à cette heure, `pynsee` ne supporte pas les projections de codes commune. 
Dans l'immédiat, après avoir installé `french-cities` depuis pypi, il faut donc
désinstaller `pynsee` puis réinstaller la version master courante depuis son repo 
github :
```
pip uninstall pynsee
pip install git+https://github.com/InseeFrLab/pynsee
```

L'installation "full" permet d'installer geopy qui est une dépendance 
optionnelle utilisable en dernier ressort.
