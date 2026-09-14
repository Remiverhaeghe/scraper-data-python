"""
Tests du service Book.
"""

from unittest.mock import patch

from book.model import Book
from book.parser import extract_next_url, parse_html
from book.service import scrape_book, scrape_books


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


def test_scrape_books():
    """Vérifie la récupération de plusieurs pages."""

    html_page_1 = """
    <ul class="pager">
        <li class="next">
            <a href="page-2.html">next</a>
        </li>
    </ul>

    <article class="product_pod">
        <h3>
            <a href="book-1.html">Book 1</a>
        </h3>
        <p class="price_color">£10.00</p>
        <p class="instock availability">In stock</p>
        <p class="star-rating One"></p>
    </article>
    """

    html_page_2 = """
    <article class="product_pod">
        <h3>
            <a href="book-2.html">Book 2</a>
        </h3>
        <p class="price_color">£20.00</p>
        <p class="instock availability">In stock</p>
        <p class="star-rating Five"></p>
    </article>
    """

    soup = parse_html(html_page_1)

    print(
        "NEXT TEST :",
        extract_next_url(soup, "https://example.com/")
    )

    with patch(
        "book.service.fetch_page",
        side_effect=[
            html_page_1,
            html_page_2
        ]
    ):
        books = scrape_books("https://example.com/")

    assert len(books) == 2

    assert books[0].title == "Book 1"
    assert books[0].price == 10.00
    assert books[0].rating == 1

    assert books[1].title == "Book 2"
    assert books[1].price == 20.00
    assert books[1].rating == 5


def test_scrape_books_with_max_pages():
    """Vérifie que le scraping s'arrête après le nombre de pages demandé."""

    html_page_1 = """
    <ul class="pager">
        <li class="next">
            <a href="page-2.html">next</a>
        </li>
    </ul>

    <article class="product_pod">
        <h3>
            <a href="book-1.html">Book 1</a>
        </h3>
        <p class="price_color">£10.00</p>
        <p class="instock availability">In stock</p>
        <p class="star-rating One"></p>
    </article>
    """

    html_page_2 = """
    <ul class="pager">
        <li class="next">
            <a href="page-3.html">next</a>
        </li>
    </ul>

    <article class="product_pod">
        <h3>
            <a href="book-2.html">Book 2</a>
        </h3>
        <p class="price_color">£20.00</p>
        <p class="instock availability">In stock</p>
        <p class="star-rating Two"></p>
    </article>
    """

    html_page_3 = """
    <article class="product_pod">
        <h3>
            <a href="book-3.html">Book 3</a>
        </h3>
        <p class="price_color">£30.00</p>
        <p class="instock availability">In stock</p>
        <p class="star-rating Three"></p>
    </article>
    """

    with patch(
        "book.service.fetch_page",
        side_effect=[
            html_page_1,
            html_page_2
        ]
    ):
        books = scrape_books(
            "https://example.com/",
            max_pages=2
        )

    assert len(books) == 2
    assert books[0].title == "Book 1"
    assert books[1].title == "Book 2"