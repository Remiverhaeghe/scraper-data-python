# ============================================================================
# Tests de l'écriture générique des fichiers CSV
# ============================================================================


import csv

from data.csv_writer import save_csv


class CsvTestItem:
    """
    Objet de test permettant de vérifier l'écriture générique.
    """

    def __init__(self, pName, pValue):
        self.name = pName
        self.value = pValue

    def to_csv_row(self):
        """
        Retourne les données de l'objet sous forme de ligne CSV.
        """

        rRow = [
            self.name,
            self.value
        ]

        return rRow


def test_save_csv(tmp_path):
    """
    Vérifie l'enregistrement d'objets dans un fichier CSV.
    """

    vFilePath = tmp_path / "data.csv"

    vItems = [
        CsvTestItem(
            "Element 1",
            10
        ),
        CsvTestItem(
            "Element 2",
            20
        )
    ]

    vColumns = [
        "name",
        "value"
    ]

    save_csv(
        vItems,
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
    Vérifie l'enregistrement d'une liste vide.
    """

    vFilePath = tmp_path / "data.csv"

    vColumns = [
        "name",
        "value"
    ]

    save_csv(
        [],
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