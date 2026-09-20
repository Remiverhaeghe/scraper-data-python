# ============================================================================
# Tests de l'orchestration du traitement des livres
# ============================================================================


from unittest.mock import patch

import pandas as pd

from book.application import process_books
from book.config import BookScrapingConfig


def test_process_books_with_refresh():
    """
    Vérifie que le scraping et la sauvegarde sont effectués
    lorsque le rafraîchissement est demandé.
    """

    vConfig = BookScrapingConfig(
        max_items=100,
        delay=1.0,
        timeout=30,
        max_pages=2,
        title="python",
        max_price=20,
        min_rating=4
    )

    vBooksScraped = [
        "book1",
        "book2"
    ]

    vBooksFiltered = pd.DataFrame([
        {
            "title": "Python débutant",
            "price": 15.0,
            "availability": "In stock",
            "rating": 5,
            "url": "https://example.com/book"
        }
    ])

    with patch(
        "book.application.books_file_exists",
        return_value=True
    ), patch(
        "book.application.scrape_books",
        return_value=vBooksScraped
    ) as vScrapeBooks, patch(
        "book.application.save_books"
    ) as vSaveBooks, patch(
        "book.application.read_books",
        return_value=vBooksFiltered
    ) as vReadBooks, patch(
        "book.application.filter_books",
        return_value=vBooksFiltered
    ) as vFilterBooks, patch(
        "book.application.display_books"
    ) as vDisplayBooks:

        process_books(
            "https://books.toscrape.com/",
            "output/books.csv",
            vConfig,
            pRefresh=True
        )

    vScrapeBooks.assert_called_once_with(
        "https://books.toscrape.com/",
        vConfig
    )

    vSaveBooks.assert_called_once_with(
        vBooksScraped,
        "output/books.csv"
    )

    vReadBooks.assert_called_once_with(
        "output/books.csv"
    )

    vFilterBooks.assert_called_once_with(
        vBooksFiltered,
        title="python",
        max_price=20,
        min_rating=4
    )

    vDisplayBooks.assert_called_once_with(
        vBooksFiltered
    )


def test_process_books_without_refresh_with_existing_file():
    """
    Vérifie que le scraping n'est pas lancé lorsque le fichier
    existe déjà et que le rafraîchissement n'est pas demandé.
    """

    vConfig = BookScrapingConfig(
        timeout=10
    )

    vBooks = pd.DataFrame([
        {
            "title": "Livre existant",
            "price": 10.0,
            "availability": "In stock",
            "rating": 5,
            "url": "https://example.com/book"
        }
    ])

    with patch(
        "book.application.books_file_exists",
        return_value=True
    ), patch(
        "book.application.scrape_books"
    ) as vScrapeBooks, patch(
        "book.application.read_books",
        return_value=vBooks
    ) as vReadBooks, patch(
        "book.application.filter_books",
        return_value=vBooks
    ) as vFilterBooks, patch(
        "book.application.display_books"
    ) as vDisplayBooks:

        process_books(
            "https://books.toscrape.com/",
            "output/books.csv",
            vConfig,
            pRefresh=False
        )

    vScrapeBooks.assert_not_called()

    vReadBooks.assert_called_once_with(
        "output/books.csv"
    )

    vFilterBooks.assert_called_once_with(
        vBooks,
        title=None,
        max_price=None,
        min_rating=None
    )

    vDisplayBooks.assert_called_once_with(
        vBooks
    )


def test_process_books_without_refresh_without_file():
    """
    Vérifie que le scraping est lancé lorsque le fichier
    n'existe pas et que le rafraîchissement n'est pas demandé.
    """

    vConfig = BookScrapingConfig(
        max_items=100,
        delay=1.0,
        timeout=30,
        max_pages=2
    )

    vBooksScraped = [
        "book1",
        "book2"
    ]

    vBooksFiltered = pd.DataFrame([
        {
            "title": "Livre récupéré",
            "price": 10.0,
            "availability": "In stock",
            "rating": 5,
            "url": "https://example.com/book"
        }
    ])

    with patch(
        "book.application.books_file_exists",
        return_value=False
    ), patch(
        "book.application.scrape_books",
        return_value=vBooksScraped
    ) as vScrapeBooks, patch(
        "book.application.save_books"
    ) as vSaveBooks, patch(
        "book.application.read_books",
        return_value=vBooksFiltered
    ) as vReadBooks, patch(
        "book.application.filter_books",
        return_value=vBooksFiltered
    ) as vFilterBooks, patch(
        "book.application.display_books"
    ) as vDisplayBooks:

        process_books(
            "https://books.toscrape.com/",
            "output/books.csv",
            vConfig,
            pRefresh=False
        )

    vScrapeBooks.assert_called_once_with(
        "https://books.toscrape.com/",
        vConfig
    )

    vSaveBooks.assert_called_once_with(
        vBooksScraped,
        "output/books.csv"
    )

    vReadBooks.assert_called_once_with(
        "output/books.csv"
    )

    vFilterBooks.assert_called_once_with(
        vBooksFiltered,
        title=None,
        max_price=None,
        min_rating=None
    )

    vDisplayBooks.assert_called_once_with(
        vBooksFiltered
    )