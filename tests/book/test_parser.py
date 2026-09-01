"""
Tests du parser HTML.
"""

from book.model import Book
from book.parser import extract_book, extract_books, parse_html


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
    book = extract_book(soup)

    assert isinstance(book, Book)
    assert book.title == "A Light in the Attic"
    assert book.price == 51.77
    assert book.availability == "In stock"
    assert book.rating == 3
    assert book.url == "catalogue/a-light-in-the-attic_1000/index.html"


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
    books = extract_books(soup)

    assert len(books) == 2

    assert books[0].title == "A Light in the Attic"
    assert books[0].price == 51.77
    assert books[0].rating == 3

    assert books[1].title == "Tipping the Velvet"
    assert books[1].price == 53.74
    assert books[1].rating == 1