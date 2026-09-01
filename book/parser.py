"""
Analyse du contenu HTML.
"""

from bs4 import BeautifulSoup

from book.model import Book
from utils.helpers import extract_rating, extract_text


def parse_html(html):
    """Transforme le HTML en objet BeautifulSoup."""

    return BeautifulSoup(html, "html.parser")

def extract_book(soup):
    """Extrait un livre depuis le HTML."""

    title_element = soup.select_one("h3 a")
    price = extract_text(soup, ".price_color")
    availability = extract_text(soup, ".availability")
    rating_element = soup.select_one(".star-rating")

    return Book(
        title=title_element.get_text(strip=True) if title_element else "",
        price=float(price.replace("£", "")) if price else 0.0,
        availability=availability,
        rating=extract_rating(rating_element),
        url=title_element.get("href", "") if title_element else ""
    )

def extract_books(soup):
    """Extrait plusieurs livres depuis une page HTML."""

    book_elements = soup.select(".product_pod")

    return [extract_book(book) for book in book_elements]