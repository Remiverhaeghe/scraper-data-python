"""
Service de scraping des livres.
"""

from scraper.http_client import fetch_page
from book.parser import extract_book, parse_html
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