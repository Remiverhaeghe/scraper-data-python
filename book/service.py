from book.parser import (
    extract_book,
    extract_books,
    extract_next_url,
    parse_html
)
from scraper.http_client import fetch_page
from scraper.pagination import scrape_paginated
from scraper.service import scrape_item
from utils.logger import get_logger

logger = get_logger(__name__)


def scrape_book(pUrl, pConfig):
    """
    Scrape un livre depuis une URL.
    """
    rBook = scrape_item(
        pUrl,
        pConfig,
        fetch_page,
        parse_html,
        extract_book
    )
    return rBook


def scrape_books(pUrl, pConfig):
    """
    Scrape plusieurs livres.
    """
    logger.info(
        "Début du scraping des livres : %s",
        pUrl
    )

    vResult = scrape_paginated(
        pUrl,
        pConfig,
        fetch_page,
        parse_html,
        extract_books,
        extract_next_url,
        "url"
    )

    logger.info(
        "Scraping terminé : %s livre(s) trouvée(s) sur %s page(s)",
        len(vResult.items),
        vResult.page_count
    )

    rResult = vResult
    return rResult