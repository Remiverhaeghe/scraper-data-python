# ============================================================================
# Tests de l'affichage des données des livres
# ============================================================================


import pandas as pd

from book.display import display_books


def test_display_books(capsys):
    """
    Vérifie l'affichage des livres.
    """

    vBooks = pd.DataFrame([
        {
            "title": "Livre 1",
            "price": 10.50,
            "availability": "In stock",
            "rating": 4,
            "url": "https://example.com/book1"
        }
    ])

    display_books(
        vBooks
    )

    vOutput = capsys.readouterr().out

    assert "Livre 1" in vOutput
    assert "10.5" in vOutput
    assert "4" in vOutput
    assert "In stock" in vOutput
    assert "1 livre(s) trouvé(s)." in vOutput


def test_display_books_empty(capsys):
    """
    Vérifie l'affichage lorsqu'aucun livre n'est trouvé.
    """

    vBooks = pd.DataFrame(
        columns=[
            "title",
            "price",
            "availability",
            "rating",
            "url"
        ]
    )

    display_books(
        vBooks
    )

    vOutput = capsys.readouterr().out

    assert "Aucun livre trouvé." in vOutput