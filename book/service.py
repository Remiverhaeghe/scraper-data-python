"""
Service de scraping des livres.
"""

from scraper.http_client import fetch_page
from book.parser import extract_book, extract_books, extract_next_url, parse_html
from utils.logger import get_logger


logger = get_logger(__name__)


def scrape_book(url):
    """Récupère et analyse un livre."""

    logger.info("Début du scraping du livre : %s", url)

    html = fetch_page(url)
    soup = parse_html(html)

    book = extract_book(soup, url)

    logger.info("Scraping du livre terminé : %s", url)

    return book

def scrape_books(url): 
    """Récupère et analyse les livres de toutes les pages."""

    books = []
    current_url = url

    logger.info("Début du scraping des livres : %s", url)

    while current_url : 
        logger.info("Scraping de la page : %s", current_url)

        html = fetch_page(current_url)
        soup = parse_html(html)

        books.extend(
            extract_books(soup, current_url)
        )

        current_url = extract_next_url(soup, current_url)

    logger.info("Scraping terminé : %s livre(s) récupéré(s)", len(books))

    return books