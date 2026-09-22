# ============================================================================
# Service de scraping des livres
# ============================================================================


from book.parser import (
    extract_book,
    extract_books,
    extract_next_url,
    parse_html
)
from scraper.http_client import fetch_page
from scraper.pagination import scrape_paginated
from utils.logger import get_logger


logger = get_logger(__name__)


def scrape_book(pUrl, pConfig):
    """
    Récupère et analyse un livre à partir de son URL.

    :param pUrl: URL du livre à récupérer.
    :param pConfig: Configuration du scraping.
    :return: Dictionnaire contenant le livre récupéré.
    """

    logger.info(
        "Début du scraping du livre : %s",
        pUrl
    )

    vHtml = fetch_page(
        pUrl,
        pConfig
    )

    vSoup = parse_html(
        vHtml
    )

    vBook = extract_book(
        vSoup,
        pUrl
    )

    logger.info(
        "Scraping du livre terminé : %s",
        pUrl
    )

    rBook = vBook

    return rBook


def scrape_books(pUrl, pConfig):
    """
    Récupère les livres présents sur plusieurs pages.

    :param pUrl: URL de départ du scraping.
    :param pConfig: Configuration du scraping.
    :return: Résultat du scraping paginé.
    """

    logger.info(
        "Début du scraping des livres : %s",
        pUrl
    )

    rResult = scrape_paginated(
        pUrl,
        pConfig,
        fetch_page,
        parse_html,
        extract_books,
        extract_next_url,
        "url"
    )

    logger.info(
        "Scraping terminé : %s livre(s) récupéré(s) sur %s page(s)",
        len(rResult.items),
        rResult.page_count
    )

    return rResult