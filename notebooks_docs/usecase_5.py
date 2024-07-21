# -*- coding: utf-8 -*-
"""
Created on Tue Jun 18 20:22:35 2024

@author: utilisateur
"""

import io
import logging
import numpy as np
import pandas as pd
from requests_cache import CachedSession
from zipfile import ZipFile

from french_cities import find_city

logging.basicConfig(level=logging.INFO)


def try_read_csv(data):
    encodings = ["utf8", "cp1252"]
    while encodings:
        x = encodings.pop()
        try:
            df = pd.read_csv(
                data,
                dtype=str,
                sep=";",
                encoding=x,
                quoting=1,
                header=0,
                encoding_errors="replace",
            )
        except UnicodeDecodeError:
            data.seek(0)
            continue
        break
    try:
        return df
    except NameError:
        raise ValueError("Aucun encoding n'est satisfaisant")


def main():

    url = "https://media.interieur.gouv.fr/rna/rna_import_20240601.zip"
    s = CachedSession()
    r = s.get(url)
    with ZipFile(io.BytesIO(r.content)) as z:
        files = z.filelist
        concat = []
        for x in files:
            obj = io.BytesIO(z.read(x.filename))
            try:
                concat.append(try_read_csv(obj))
            except ValueError:
                raise ValueError(f"Erreur sur {x}")
        df = pd.concat(concat, ignore_index=True)

    df.info()

    # Retraitement des codes postaux manifestement erronés
    ix = df[~df.adrs_codepostal.fillna("").str.match("[0-9AB]{5}")].index
    df.loc[ix, "adrs_codepostal"] = np.nan
    df["adrs_codepostal"] = df["adrs_codepostal"].replace("00000", np.nan)

    df = find_city(
        df,
        year="last",
        x=False,
        y=False,
        epsg=False,
        city="libcom",
        address=False,
        postcode="adrs_codepostal",
        use_nominatim_backend=True,
        field_output="codeInsee",
    )

    errors = (
        df[(df["codeInsee"].isnull()) & (df["libcom"].notnull())][
            ["libcom", "adrs_codepostal"]
        ]
        .drop_duplicates()
        .sort_values("adrs_codepostal")
    )
    errors.to_csv("test.csv")
    return df


if __name__ == "__main__":
    df = main()
