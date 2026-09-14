import pandas as pd

from data.display import display_books


def test_display_books(capsys):
    """Vérifie l'affichage des livres."""

    books = pd.DataFrame([
        {
            "title": "Livre 1",
            "price": 10.50,
            "availability": "In stock",
            "rating": 4,
            "url": "https://example.com/book1"
        }
    ])

    display_books(books)

    output = capsys.readouterr().out

    assert "Livre 1" in output
    assert "10.5" in output
    assert "4" in output
    assert "In stock" in output
    assert "1 livre(s) trouvé(s)." in output


def test_display_books_empty(capsys):
    """Vérifie l'affichage lorsqu'aucun livre n'est trouvé."""

    books = pd.DataFrame(
        columns=[
            "title",
            "price",
            "availability",
            "rating",
            "url"
        ]
    )

    display_books(books)

    output = capsys.readouterr().out

    assert "Aucun livre trouvé." in output