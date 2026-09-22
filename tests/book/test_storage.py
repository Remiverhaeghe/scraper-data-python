# ============================================================================
# Tests du stockage des livres
# ============================================================================


import csv
from pathlib import Path

import pandas as pd
import pytest

from book.csv_schema import BOOK_COLUMNS
from book.storage import save_books


def test_save_books(tmp_path):
    """
    Vérifie l'enregistrement des livres dans un fichier CSV.
    """

    vFilePath = tmp_path / "books.csv"

    vBooks = pd.DataFrame(
        [
            {
                "title": "Book 1",
                "price": 10.00,
                "availability": "In stock",
                "rating": 4,
                "url": "https://example.com/book-1"
            },
            {
                "title": "Book 2",
                "price": 20.00,
                "availability": "In stock",
                "rating": 5,
                "url": "https://example.com/book-2"
            }
        ]
    )

    save_books(
        vBooks,
        vFilePath
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

    assert vRows[0] == BOOK_COLUMNS

    assert vRows[1] == [
        "Book 1",
        "10.0",
        "In stock",
        "4",
        "https://example.com/book-1"
    ]

    assert vRows[2] == [
        "Book 2",
        "20.0",
        "In stock",
        "5",
        "https://example.com/book-2"
    ]


def test_save_empty_books(tmp_path):
    """
    Vérifie l'enregistrement d'un DataFrame de livres vide.
    """

    vFilePath = tmp_path / "books.csv"

    vBooks = pd.DataFrame(
        columns=BOOK_COLUMNS
    )

    save_books(
        vBooks,
        vFilePath
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
        BOOK_COLUMNS
    ]


def test_save_books_logs_error_when_file_cannot_be_written(
    tmp_path,
    monkeypatch
):
    """
    Vérifie qu'une erreur d'écriture est enregistrée dans les logs.
    """

    vFilePath = tmp_path / "books.csv"

    def mock_to_csv(*args, **kwargs):
        raise PermissionError(
            "Accès refusé"
        )

    monkeypatch.setattr(
        pd.DataFrame,
        "to_csv",
        mock_to_csv
    )

    vBooks = pd.DataFrame(
        [
            {
                "title": "Book 1",
                "price": 10.00,
                "availability": "In stock",
                "rating": 4,
                "url": "https://example.com/book-1"
            }
        ]
    )

    with pytest.raises(PermissionError):
        save_books(
            vBooks,
            vFilePath
        )