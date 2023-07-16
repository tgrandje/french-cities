# french-cities
Toolbox on french cities: set vintage, find departments, find cities...


# Installation

`pip install french-cities`


# Usage

## Setting INSEE API keys
`french-cities` uses `pynsee` under the hood. For it to work, you need to set
the credentials up. You can set up to four environment variables:
* insee_key
* insee_secret, 
* http_proxy (if accessing web behind a corporate proxy)
* https_proxy (if accessing web behind a corporate proxy)

Please refer to `pynsee`'s documentation to help configure the API's access.

## Session management
Note that `pynsee` uses it's own web session. Every Session object you will pass
to `french-cities` will **NOT** be shared with `pynsee`. This explains the
possibility to pass a session as an argument to `french-cities` functions,
even if you had to configure the corporate proxy through environment variables
for `pynsee`.

## Basic usage


#TODO
docstrings in english
refacto departement_finder
methodes __all__
README
push to pypi