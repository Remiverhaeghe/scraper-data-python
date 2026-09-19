# ============================================================================
# Tests du stockage des livres
# ============================================================================


import csv
from pathlib import Path

import pytest

from book.model import Book
from book.storage import save_books


def test_save_books(tmp_path):
    """
    Vérifie l'enregistrement des livres dans un fichier CSV.
    """

    vFilePath = tmp_path / "books.csv"

    vBooks = [
        Book(
            title="Book 1",
            price=10.00,
            availability="In stock",
            rating=4,
            url="https://example.com/book-1"
        ),
        Book(
            title="Book 2",
            price=20.00,
            availability="In stock",
            rating=5,
            url="https://example.com/book-2"
        )
    ]

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

    assert vRows[0] == [
        "title",
        "price",
        "availability",
        "rating",
        "url"
    ]

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
    Vérifie l'enregistrement d'une liste de livres vide.
    """

    vFilePath = tmp_path / "books.csv"

    save_books(
        [],
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

    assert vRows == [[
        "title",
        "price",
        "availability",
        "rating",
        "url"
    ]]


def test_save_books_logs_error_when_file_cannot_be_written(
    tmp_path,
    monkeypatch
):
    """
    Vérifie qu'une erreur d'écriture est enregistrée dans les logs.
    """

    vFilePath = tmp_path / "books.csv"

    def mock_open(*args, **kwargs):
        raise PermissionError(
            "Accès refusé"
        )

    monkeypatch.setattr(
        Path,
        "open",
        mock_open
    )

    vBooks = [
        Book(
            title="Book 1",
            price=10.00,
            availability="In stock",
            rating=4,
            url="https://example.com/book-1"
        )
    ]

    with pytest.raises(PermissionError):
        save_books(
            vBooks,
            vFilePath
        )