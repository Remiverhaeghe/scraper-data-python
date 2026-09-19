# ============================================================================
# Service de scraping des livres
# ============================================================================


from book.config import BookScrapingConfig
from book.parser import (
    extract_book,
    extract_books,
    extract_next_url,
    parse_html
)
from scraper.http_client import fetch_page
from utils.logger import get_logger


logger = get_logger(__name__)


def scrape_book(pUrl, pConfig):
    """
    Récupère et analyse un livre à partir de son URL.

    :param pUrl: URL du livre à récupérer.
    :param pConfig: Configuration du scraping.
    :return: Livre récupéré.
    """

    logger.info(
        "Début du scraping du livre : %s",
        pUrl
    )

    vHtml = fetch_page(
        pUrl,
        pTimeout=pConfig.timeout
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
    :return: Liste des livres récupérés.
    """

    vBooks = []
    vCurrentUrl = pUrl
    vPageCount = 0

    logger.info(
        "Début du scraping des livres : %s",
        pUrl
    )

    while vCurrentUrl:
        # Vérification du nombre maximum de pages
        if (
            pConfig.max_pages is not None
            and vPageCount >= pConfig.max_pages
        ):
            break

        # Vérification du nombre maximum de livres
        if (
            pConfig.max_items is not None
            and len(vBooks) >= pConfig.max_items
        ):
            break

        vPageCount += 1

        logger.info(
            "Scraping de la page %s : %s",
            vPageCount,
            vCurrentUrl
        )

        vHtml = fetch_page(
            vCurrentUrl,
            pTimeout=pConfig.timeout
        )

        vSoup = parse_html(
            vHtml
        )

        vBooks.extend(
            extract_books(
                vSoup,
                vCurrentUrl
            )
        )

        # Suppression des livres supplémentaires si la limite est atteinte
        if (
            pConfig.max_items is not None
            and len(vBooks) > pConfig.max_items
        ):
            vBooks = vBooks[
                :pConfig.max_items
            ]

        vCurrentUrl = extract_next_url(
            vSoup,
            vCurrentUrl
        )

    logger.info(
        "Scraping terminé : %s livre(s) récupéré(s)",
        len(vBooks)
    )

    rBooks = vBooks

    return rBooks