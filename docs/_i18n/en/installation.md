# Installation

`pip install french-cities[full]`

Note that at this instant, `pynsee` doesn't support communal projection.
After installing `french-cities` from pypi, please uninstall pynsee and replace
it with the current master:
```
pip uninstall pynsee
pip install git+https://github.com/InseeFrLab/pynsee
```

Note that the "full" installation will also install geopy, which might use
Nominatim API for city recognition as a last resort.
