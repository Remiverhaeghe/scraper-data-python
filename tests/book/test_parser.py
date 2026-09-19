# ============================================================================
# Tests du parser HTML des livres
# ============================================================================


import pytest

from book.model import Book
from book.parser import (
    extract_book,
    extract_books,
    extract_next_url,
    parse_html
)


def test_parse_html():
    """
    Vérifie la conversion du HTML en objet BeautifulSoup.
    """

    vHtml = "<h1>Développeur Python</h1>"

    vSoup = parse_html(
        vHtml
    )

    assert vSoup.h1.text == "Développeur Python"


def test_extract_book():
    """
    Vérifie l'extraction d'un livre.
    """

    vHtml = """
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

    vSoup = parse_html(
        vHtml
    )

    vBook = extract_book(
        vSoup,
        "https://books.toscrape.com/"
    )

    assert isinstance(vBook, Book)
    assert vBook.title == "A Light in the Attic"
    assert vBook.price == 51.77
    assert vBook.availability == "In stock"
    assert vBook.rating == 3
    assert vBook.url == (
        "https://books.toscrape.com/"
        "catalogue/a-light-in-the-attic_1000/index.html"
    )


def test_extract_books():
    """
    Vérifie l'extraction de plusieurs livres.
    """

    vHtml = """
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

    vSoup = parse_html(
        vHtml
    )

    vBooks = extract_books(
        vSoup,
        "https://books.toscrape.com/catalogue/"
    )

    assert len(vBooks) == 2

    assert vBooks[0].title == "A Light in the Attic"
    assert vBooks[0].price == 51.77
    assert vBooks[0].rating == 3
    assert vBooks[0].url == (
        "https://books.toscrape.com/catalogue/"
        "book-1.html"
    )

    assert vBooks[1].title == "Tipping the Velvet"
    assert vBooks[1].price == 53.74
    assert vBooks[1].rating == 1
    assert vBooks[1].url == (
        "https://books.toscrape.com/catalogue/"
        "book-2.html"
    )


def test_extract_book_invalid_price():
    """
    Vérifie qu'une erreur de prix est correctement remontée.
    """

    vHtml = """
    <article class="product_pod">
        <h3>
            <a href="book-1.html">A Light in the Attic</a>
        </h3>
        <p class="price_color">£ABC</p>
        <p class="availability">In stock</p>
        <p class="star-rating Three"></p>
    </article>
    """

    vSoup = parse_html(
        vHtml
    )

    with pytest.raises(ValueError):
        extract_book(
            vSoup,
            "https://books.toscrape.com/catalogue/"
        )


def test_extract_next_url():
    """
    Vérifie l'extraction de l'URL de la page suivante.
    """

    vHtml = """
    <ul class="pager">
        <li class="next">
            <a href="catalogue/page-2.html">next</a>
        </li>
    </ul>
    """

    vSoup = parse_html(
        vHtml
    )

    rUrl = extract_next_url(
        vSoup,
        "https://books.toscrape.com/"
    )

    assert rUrl == (
        "https://books.toscrape.com/"
        "catalogue/page-2.html"
    )


def test_extract_next_url_without_next_page():
    """
    Vérifie l'absence de page suivante.
    """

    vHtml = """
    <ul class="pager">
    </ul>
    """

    vSoup = parse_html(
        vHtml
    )

    rUrl = extract_next_url(
        vSoup,
        "https://books.toscrape.com/"
    )

    assert rUrl == ""


def test_extract_book_with_missing_data():
    """
    Vérifie le comportement lorsque certaines données sont absentes.
    """

    vHtml = """
    <article class="product_pod">
        <h3>
            <a href="book.html">Mon livre</a>
        </h3>
    </article>
    """

    vSoup = parse_html(
        vHtml
    )

    vBook = extract_book(
        vSoup,
        "https://books.toscrape.com/"
    )

    assert vBook.title == "Mon livre"
    assert vBook.price == 0.0
    assert vBook.availability == ""
    assert vBook.rating == 0
    assert vBook.url == "https://books.toscrape.com/book.html"


def test_extract_books_without_books():
    """
    Vérifie qu'une page sans livre retourne une liste vide.
    """

    vHtml = """
    <html>
        <body>
            <h1>Page sans livre</h1>
        </body>
    </html>
    """

    vSoup = parse_html(
        vHtml
    )

    vBooks = extract_books(
        vSoup,
        "https://books.toscrape.com/"
    )

    assert vBooks == []


def test_extract_book_without_title():
    """
    Vérifie le comportement lorsqu'un livre n'a pas de titre.
    """

    vHtml = """
    <article class="product_pod">
        <p class="price_color">£10.00</p>
        <p class="availability">In stock</p>
        <p class="star-rating Three"></p>
    </article>
    """

    vSoup = parse_html(
        vHtml
    )

    vBook = extract_book(
        vSoup,
        "https://books.toscrape.com/"
    )

    assert vBook.title == ""
    assert vBook.price == 10.00
    assert vBook.availability == "In stock"
    assert vBook.rating == 3
    assert vBook.url == ""


def test_extract_book_without_url():
    """
    Vérifie le comportement lorsqu'un livre n'a pas d'URL.
    """

    vHtml = """
    <article class="product_pod">
        <h3>
            <a>Mon livre</a>
        </h3>
        <p class="price_color">£10.00</p>
        <p class="availability">In stock</p>
        <p class="star-rating Three"></p>
    </article>
    """

    vSoup = parse_html(
        vHtml
    )

    vBook = extract_book(
        vSoup,
        "https://books.toscrape.com/"
    )

    assert vBook.title == "Mon livre"
    assert vBook.price == 10.00
    assert vBook.availability == "In stock"
    assert vBook.rating == 3
    assert vBook.url == ""