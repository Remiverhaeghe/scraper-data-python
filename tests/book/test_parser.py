"""
Tests du parser HTML.
"""
import pytest
from book.model import Book
from book.parser import extract_book, extract_books, extract_next_url, parse_html


def test_parse_html():
    """Vérifie la conversion du HTML."""

    html = "<h1>Développeur Python</h1>"

    soup = parse_html(html)

    assert soup.h1.text == "Développeur Python"

def test_extract_book():
    """Vérifie l'extraction d'un livre."""

    html = """
    <article class="product_pod">
        <h3>
            <a href="catalogue/a-light-in-the-attic_1000/index.html">
                A Light in the Attic
            </a>
        </h3>

        <p class="price_color">£51.77</p>

        <p class="instock availability">
            In stock
        </p>

        <p class="star-rating Three"></p>
    </article>
    """

    soup = parse_html(html)
    book = extract_book(soup, "https://books.toscrape.com/")

    assert isinstance(book, Book)
    assert book.title == "A Light in the Attic"
    assert book.price == 51.77
    assert book.availability == "In stock"
    assert book.rating == 3
    assert book.url == (
        "https://books.toscrape.com/"
        "catalogue/a-light-in-the-attic_1000/index.html")


def test_extract_books():
    """Vérifie l'extraction de plusieurs livres."""

    html = """
    <article class="product_pod">
        <h3>
            <a href="book-1.html">A Light in the Attic</a>
        </h3>
        <p class="price_color">£51.77</p>
        <p class="instock availability">In stock</p>
        <p class="star-rating Three"></p>
    </article>

    <article class="product_pod">
        <h3>
            <a href="book-2.html">Tipping the Velvet</a>
        </h3>
        <p class="price_color">£53.74</p>
        <p class="instock availability">In stock</p>
        <p class="star-rating One"></p>
    </article>
    """

    soup = parse_html(html)
    books = extract_books(soup, "https://books.toscrape.com/catalogue/")

    assert len(books) == 2

    assert books[0].title == "A Light in the Attic"
    assert books[0].price == 51.77
    assert books[0].rating == 3
    assert books[0].url == (
        "https://books.toscrape.com/catalogue/"
        "book-1.html"
    )

    assert books[1].title == "Tipping the Velvet"
    assert books[1].price == 53.74
    assert books[1].rating == 1
    assert books[1].url == (
        "https://books.toscrape.com/catalogue/"
        "book-2.html"
    )

def test_extract_book_invalid_price():
    """Vérifie qu'une erreur de prix est bien remontée."""

    html = """
    <article class="product_pod">
        <h3>
            <a href="book-1.html">A Light in the Attic</a>
        </h3>
        <p class="price_color">£ABC</p>
        <p class="availability">In stock</p>
        <p class="star-rating Three"></p>
    </article>
    """

    soup = parse_html(html)

    with pytest.raises(ValueError):
        extract_book(soup,"https://books.toscrape.com/catalogue/" )


def test_extract_next_url():
    """Vérifie l'extraction de l'URL de la page suivante."""

    html = """
    <ul class="pager">
        <li class="next">
            <a href="catalogue/page-2.html">next</a>
        </li>
    </ul>
    """

    soup = parse_html(html)

    result = extract_next_url(
        soup,
        "https://books.toscrape.com/"
    )

    assert result == (
        "https://books.toscrape.com/"
        "catalogue/page-2.html"
    )


def test_extract_next_url_without_next_page():
    """Vérifie l'absence de page suivante."""

    html = """
    <ul class="pager">
    </ul>
    """

    soup = parse_html(html)

    result = extract_next_url(
        soup,
        "https://books.toscrape.com/"
    )

    assert result == ""

def test_extract_book_with_missing_data():
    """Vérifie le comportement lorsque certaines données sont absentes."""

    html = """
    <article class="product_pod">
        <h3>
            <a href="book.html">Mon livre</a>
        </h3>
    </article>
    """

    soup = parse_html(html)

    book = extract_book(
        soup,
        "https://books.toscrape.com/"
    )

    assert book.title == "Mon livre"
    assert book.price == 0.0
    assert book.availability == ""
    assert book.rating == 0
    assert book.url == "https://books.toscrape.com/book.html"

def test_extract_books_without_books():
    """Vérifie qu'une page sans livre retourne une liste vide."""

    html = """
    <html>
        <body>
            <h1>Page sans livre</h1>
        </body>
    </html>
    """

    soup = parse_html(html)

    books = extract_books(
        soup,
        "https://books.toscrape.com/"
    )

    assert books == []