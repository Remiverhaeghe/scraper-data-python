"""
Tests du stockage des livres.
"""

import csv

from book.model import Book
from book.storage import save_books


def test_save_books(tmp_path):
    """Vérifie l'enregistrement des livres dans un fichier CSV."""

    file_path = tmp_path / "books.csv"

    books = [
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

    save_books(books, file_path)

    assert file_path.exists()

    with file_path.open(
        mode="r",
        encoding="utf-8",
        newline=""
    ) as file:
        rows = list(csv.reader(file))

    assert rows[0] == [
        "title",
        "price",
        "availability",
        "rating",
        "url"
    ]

    assert rows[1] == [
        "Book 1",
        "10.0",
        "In stock",
        "4",
        "https://example.com/book-1"
    ]

    assert rows[2] == [
        "Book 2",
        "20.0",
        "In stock",
        "5",
        "https://example.com/book-2"
    ]

def test_save_empty_books(tmp_path):
    """Vérifie l'enregistrement d'une liste de livres vide."""

    file_path = tmp_path / "books.csv"

    save_books([], file_path)

    assert file_path.exists()

    with file_path.open(
        mode="r",
        encoding="utf-8",
        newline=""
    ) as file:
        rows = list(csv.reader(file))

    assert rows == [[
        "title",
        "price",
        "availability",
        "rating",
        "url"
    ]]