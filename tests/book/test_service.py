"""
Tests du service Book.
"""

from unittest.mock import patch

from book.model import Book
from book.service import scrape_book


def test_scrape_book():
    """Vérifie la récupération d'un livre."""

    html = """
    <article class="product_pod">
        <h3>
            <a href="book-1.html">A Light in the Attic</a>
        </h3>

        <p class="price_color">£51.77</p>

        <p class="instock availability">
            In stock
        </p>

        <p class="star-rating Three"></p>
    </article>
    """

    with patch(
        "book.service.fetch_page",
        return_value=html
    ):
        book = scrape_book("https://example.com/book")

    assert isinstance(book, Book)
    assert book.title == "A Light in the Attic"
    assert book.price == 51.77
    assert book.availability == "In stock"
    assert book.rating == 3
    assert book.url == "https://example.com/book-1.html"