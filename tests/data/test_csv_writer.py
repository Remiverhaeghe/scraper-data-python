# ============================================================================
# Tests de l'écriture générique des fichiers CSV
# ============================================================================


import csv

import pandas as pd

from data.csv_writer import save_csv


def test_save_csv(tmp_path):
    """
    Vérifie l'enregistrement d'un DataFrame dans un fichier CSV.
    """

    vFilePath = tmp_path / "data.csv"

    vDataFrame = pd.DataFrame(
        [
            {
                "name": "Element 1",
                "value": 10
            },
            {
                "name": "Element 2",
                "value": 20
            }
        ]
    )

    vColumns = [
        "name",
        "value"
    ]

    save_csv(
        vDataFrame,
        vFilePath,
        vColumns
    )

    assert vFilePath.exists()

    with vFilePath.open(
        mode="r",
        encoding="utf-8",
        newline=""
    ) as vFile:

        vRows = list(
            csv.reader(vFile)
        )

    assert vRows == [
        ["name", "value"],
        ["Element 1", "10"],
        ["Element 2", "20"]
    ]


def test_save_empty_csv(tmp_path):
    """
    Vérifie l'enregistrement d'un DataFrame vide.
    """

    vFilePath = tmp_path / "data.csv"

    vDataFrame = pd.DataFrame(
        columns=[
            "name",
            "value"
        ]
    )

    vColumns = [
        "name",
        "value"
    ]

    save_csv(
        vDataFrame,
        vFilePath,
        vColumns
    )

    assert vFilePath.exists()

    with vFilePath.open(
        mode="r",
        encoding="utf-8",
        newline=""
    ) as vFile:

        vRows = list(
            csv.reader(vFile)
        )

    assert vRows == [
        ["name", "value"]
    ]