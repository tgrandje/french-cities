# french-cities
Python toolbox package regarding french cities


# Installation

## Standard
Pour une installation sur une infrastructure moderne :
`pip install french-cities[standard]`


## Legacy
Do you want french-cities to run on an old CPU (e.g. dating from before 2011)?
Install `pip install french-cities[legacy]`.
This will use `polars-lts-cpu` (instead of `polars`) which is compiled without 
[avx](https://en.wikipedia.org/wiki/Advanced_Vector_Extensions) target features.