import pandas as pd

from data.filter import filter_books


def test_filter_books():
    """Vérifie le filtrage des livres par prix et note."""

    books = pd.DataFrame([
        {
            "title": "Livre 1",
            "price": 10.0,
            "availability": "In stock",
            "rating": 5,
            "url": "https://example.com/book1"
        },
        {
            "title": "Livre 2",
            "price": 25.0,
            "availability": "In stock",
            "rating": 5,
            "url": "https://example.com/book2"
        },
        {
            "title": "Livre 3",
            "price": 15.0,
            "availability": "In stock",
            "rating": 3,
            "url": "https://example.com/book3"
        }
    ])

    result = filter_books(
        books,
        max_price=20,
        min_rating=4
    )

    assert len(result) == 1
    assert result.iloc[0]["title"] == "Livre 1"


def test_filter_books_by_title():
    """Vérifie le filtrage des livres par titre."""

    books = pd.DataFrame([
        {
            "title": "Python pour débutants",
            "price": 10.0,
            "availability": "In stock",
            "rating": 5,
            "url": "https://example.com/book1"
        },
        {
            "title": "Apprendre Java",
            "price": 15.0,
            "availability": "In stock",
            "rating": 4,
            "url": "https://example.com/book2"
        },
        {
            "title": "Python avancé",
            "price": 20.0,
            "availability": "In stock",
            "rating": 4,
            "url": "https://example.com/book3"
        }
    ])

    result = filter_books(
        books,
        title="python"
    )

    assert len(result) == 2
    assert result.iloc[0]["title"] == "Python pour débutants"
    assert result.iloc[1]["title"] == "Python avancé"

def test_filter_books_with_all_criteria():
    """Vérifie la combinaison des critères de recherche."""

    books = pd.DataFrame([
        {
            "title": "Python débutant",
            "price": 15.0,
            "availability": "In stock",
            "rating": 5,
            "url": "https://example.com/book1"
        },
        {
            "title": "Python avancé",
            "price": 25.0,
            "availability": "In stock",
            "rating": 5,
            "url": "https://example.com/book2"
        },
        {
            "title": "Java débutant",
            "price": 10.0,
            "availability": "In stock",
            "rating": 5,
            "url": "https://example.com/book3"
        },
        {
            "title": "Python ancien",
            "price": 10.0,
            "availability": "In stock",
            "rating": 3,
            "url": "https://example.com/book4"
        }
    ])

    result = filter_books(
        books,
        title="python",
        max_price=20,
        min_rating=4
    )

    assert len(result) == 1
    assert result.iloc[0]["title"] == "Python débutant"


def test_filter_books_title_with_special_characters():
    """Vérifie que la recherche de titre traite les caractères spéciaux comme du texte."""

    books = pd.DataFrame([
        {
            "title": "C++ pour débutants",
            "price": 20.0,
            "availability": "In stock",
            "rating": 4,
            "url": "https://example.com/book"
        },
        {
            "title": "Python avancé",
            "price": 15.0,
            "availability": "In stock",
            "rating": 5,
            "url": "https://example.com/book-2"
        }
    ])

    result = filter_books(
        books,
        title="C++"
    )

    assert len(result) == 1
    assert result.iloc[0]["title"] == "C++ pour débutants"

def test_filter_books_with_all_filters():
    """Vérifie que tous les filtres sont appliqués ensemble."""

    books = pd.DataFrame([
        {
            "title": "Python débutant",
            "price": 15.0,
            "availability": "In stock",
            "rating": 5,
            "url": "https://example.com/book-1"
        },
        {
            "title": "Python avancé",
            "price": 25.0,
            "availability": "In stock",
            "rating": 5,
            "url": "https://example.com/book-2"
        },
        {
            "title": "Java débutant",
            "price": 10.0,
            "availability": "In stock",
            "rating": 5,
            "url": "https://example.com/book-3"
        },
        {
            "title": "Python moyen",
            "price": 15.0,
            "availability": "In stock",
            "rating": 3,
            "url": "https://example.com/book-4"
        }
    ])

    result = filter_books(
        books,
        title="python",
        max_price=20,
        min_rating=4
    )

    assert len(result) == 1
    assert result.iloc[0]["title"] == "Python débutant"