# ============================================================================
# Tests du service de scraping des livres
# ============================================================================


from unittest.mock import patch

from book.config import BookScrapingConfig
from book.model import Book
from book.service import scrape_book, scrape_books


def test_scrape_book():
    """
    Vérifie le scraping d'un livre.
    """

    vConfig = BookScrapingConfig(
        timeout=30
    )

    vBook = Book(
        title="Python",
        price=10.0,
        availability="In stock",
        rating=5,
        url="https://books.toscrape.com/catalogue/python.html"
    )

    with patch(
        "book.service.fetch_page",
        return_value="<html>Test</html>"
    ) as vFetchPage, patch(
        "book.service.parse_html"
    ) as vParseHtml, patch(
        "book.service.extract_book",
        return_value=vBook
    ):

        rBook = scrape_book(
            "https://books.toscrape.com/catalogue/python.html",
            vConfig
        )

    vFetchPage.assert_called_once_with(
        "https://books.toscrape.com/catalogue/python.html",
        vConfig
    )

    vParseHtml.assert_called_once_with(
        "<html>Test</html>"
    )

    assert rBook == vBook


def test_scrape_books():
    """
    Vérifie le scraping de plusieurs pages et la suppression
    des doublons.
    """

    vConfig = BookScrapingConfig(
        timeout=20,
        max_pages=2
    )

    vBook = Book(
        title="Python",
        price=10.0,
        availability="In stock",
        rating=5,
        url="https://books.toscrape.com/catalogue/python.html"
    )

    vSoup = object()

    with patch(
        "book.service.fetch_page",
        return_value="<html>Test</html>"
    ) as vFetchPage, patch(
        "book.service.parse_html",
        return_value=vSoup
    ), patch(
        "book.service.extract_books",
        side_effect=[
            [vBook],
            [vBook]
        ]
    ), patch(
        "book.service.extract_next_url",
        side_effect=[
            "https://books.toscrape.com/page-2.html",
            ""
        ]
    ):

        rResult = scrape_books(
            "https://books.toscrape.com/",
            vConfig
        )

    assert rResult.items == [
        vBook
    ]

    assert rResult.page_count == 2
    assert rResult.duration_seconds >= 0
    assert rResult.status == "success"
    assert rResult.error_message is None

    assert vFetchPage.call_count == 2

    vFetchPage.assert_any_call(
        "https://books.toscrape.com/",
        vConfig
    )

    vFetchPage.assert_any_call(
        "https://books.toscrape.com/page-2.html",
        vConfig
    )


def test_scrape_books_with_max_items():
    """
    Vérifie que le nombre maximum d'éléments est respecté.
    """

    vConfig = BookScrapingConfig(
        timeout=10,
        max_items=2
    )

    vBooks = [
        Book(
            title="Book 1",
            price=10.0,
            availability="In stock",
            rating=5,
            url="https://books.toscrape.com/book1.html"
        ),
        Book(
            title="Book 2",
            price=20.0,
            availability="In stock",
            rating=4,
            url="https://books.toscrape.com/book2.html"
        ),
        Book(
            title="Book 3",
            price=30.0,
            availability="In stock",
            rating=3,
            url="https://books.toscrape.com/book3.html"
        )
    ]

    vSoup = object()

    with patch(
        "book.service.fetch_page",
        return_value="<html>Test</html>"
    ), patch(
        "book.service.parse_html",
        return_value=vSoup
    ), patch(
        "book.service.extract_books",
        return_value=vBooks
    ), patch(
        "book.service.extract_next_url",
        return_value="https://books.toscrape.com/page-2.html"
    ):

        rResult = scrape_books(
            "https://books.toscrape.com/",
            vConfig
        )

    assert len(rResult.items) == 2
    assert rResult.items == vBooks[:2]

    assert rResult.page_count == 1
    assert rResult.duration_seconds >= 0
    assert rResult.status == "success"
    assert rResult.error_message is None


def test_scrape_books_with_max_pages():
    """
    Vérifie que le nombre maximum de pages est respecté.
    """

    vConfig = BookScrapingConfig(
        timeout=10,
        max_pages=1
    )

    vBook = Book(
        title="Python",
        price=10.0,
        availability="In stock",
        rating=5,
        url="https://books.toscrape.com/python.html"
    )

    vSoup = object()

    with patch(
        "book.service.fetch_page",
        return_value="<html>Test</html>"
    ) as vFetchPage, patch(
        "book.service.parse_html",
        return_value=vSoup
    ), patch(
        "book.service.extract_books",
        return_value=[vBook]
    ), patch(
        "book.service.extract_next_url",
        return_value="https://books.toscrape.com/page-2.html"
    ):

        rResult = scrape_books(
            "https://books.toscrape.com/",
            vConfig
        )

    assert rResult.items == [
        vBook
    ]

    assert rResult.page_count == 1
    assert rResult.duration_seconds >= 0
    assert rResult.status == "success"
    assert rResult.error_message is None

    assert vFetchPage.call_count == 1