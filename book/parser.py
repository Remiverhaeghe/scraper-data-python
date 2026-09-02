"""
Analyse du contenu HTML.
"""

from bs4 import BeautifulSoup

from book.model import Book
from utils.helpers import extract_price, extract_rating, extract_text
from utils.url import build_absolute_url
from utils.logger import get_logger


logger = get_logger(__name__)


def parse_html(html):
    """Transforme le HTML en objet BeautifulSoup."""

    return BeautifulSoup(html, "html.parser")


def extract_book(soup, base_url):
    """Extrait un livre depuis le HTML."""

    try:
        title_element = soup.select_one("h3 a")
        price = extract_text(soup, ".price_color")
        availability = extract_text(soup, ".availability")
        rating_element = soup.select_one(".star-rating")

        relative_url = (
            title_element.get("href", "")
            if title_element
            else ""
        )

        return Book(
            title=title_element.get_text(strip=True) if title_element else "",
            price=extract_price(price),
            availability=availability,
            rating=extract_rating(rating_element),
            url=build_absolute_url(base_url, relative_url)
        )

    except Exception:
        logger.exception("Erreur lors de l'analyse d'un livre")
        raise

def extract_books(soup, base_url):
    """Extrait plusieurs livres depuis une page HTML."""

    book_elements = soup.select(".product_pod")

    logger.info(
        "%s livre(s) trouvé(s) dans la page",
        len(book_elements)
    )

    return [
        extract_book(book, base_url)
        for book in book_elements
    ]