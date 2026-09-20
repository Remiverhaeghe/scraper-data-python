# ============================================================================
# Tests de la lecture générique des fichiers CSV
# ============================================================================


import pandas as pd
import pytest

from data.csv_reader import file_exists, read_csv


def test_file_exists(tmp_path):
    """
    Vérifie si un fichier existe.
    """

    vFilePath = tmp_path / "data.csv"

    vFilePath.touch()

    rExists = file_exists(
        vFilePath
    )

    assert rExists is True


def test_file_does_not_exist(tmp_path):
    """
    Vérifie qu'un fichier inexistant est correctement détecté.
    """

    vFilePath = tmp_path / "data.csv"

    rExists = file_exists(
        vFilePath
    )

    assert rExists is False


def test_read_csv(tmp_path):
    """
    Vérifie la lecture d'un fichier CSV.
    """

    vFilePath = tmp_path / "data.csv"

    vFilePath.write_text(
        "name,value\n"
        "Element 1,10\n"
        "Element 2,20\n",
        encoding="utf-8"
    )

    rData = read_csv(
        vFilePath
    )

    assert len(rData) == 2
    assert rData.iloc[0]["name"] == "Element 1"
    assert rData.iloc[0]["value"] == 10


def test_read_empty_csv(tmp_path):
    """
    Vérifie la lecture d'un fichier CSV vide.
    """

    vFilePath = tmp_path / "data.csv"

    vFilePath.touch()

    rData = read_csv(
        vFilePath,
        pColumns=[
            "name",
            "value"
        ]
    )

    assert rData.empty
    assert list(rData.columns) == [
        "name",
        "value"
    ]


def test_read_csv_file_does_not_exist(tmp_path):
    """
    Vérifie qu'une erreur est levée lorsque le fichier CSV n'existe pas.
    """

    vFilePath = tmp_path / "data.csv"

    with pytest.raises(FileNotFoundError):
        read_csv(
            vFilePath
        )