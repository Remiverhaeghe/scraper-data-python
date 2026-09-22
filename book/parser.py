# ============================================================================
# Analyse et extraction des données HTML des livres
# ============================================================================


import pandas as pd

from bs4 import BeautifulSoup

from utils.helpers import extract_price, extract_rating, extract_text
from utils.logger import get_logger
from utils.url import build_absolute_url


logger = get_logger(__name__)


def parse_html(pHtml):
    """
    Transforme le HTML en objet BeautifulSoup.

    :param pHtml: Contenu HTML à analyser.
    :return: Objet BeautifulSoup.
    """

    rSoup = BeautifulSoup(
        pHtml,
        "html.parser"
    )

    return rSoup


def extract_book(pSoup, pBaseUrl):
    """
    Extrait un livre depuis le HTML.

    :param pSoup: Élément HTML contenant le livre.
    :param pBaseUrl: URL de base permettant de construire l'URL absolue.
    :return: Dictionnaire contenant les données du livre.
    """

    try:
        vTitleElement = pSoup.select_one(
            "h3 a"
        )

        vPrice = extract_text(
            pSoup,
            ".price_color"
        )

        vAvailability = extract_text(
            pSoup,
            ".availability"
        )

        vRatingElement = pSoup.select_one(
            ".star-rating"
        )

        vRelativeUrl = (
            vTitleElement.get(
                "href",
                ""
            )
            if vTitleElement
            else ""
        )

        vBook = {
            "title": (
                vTitleElement.get_text(
                    strip=True
                )
                if vTitleElement
                else ""
            ),
            "price": extract_price(
                vPrice
            ),
            "availability": vAvailability,
            "rating": extract_rating(
                vRatingElement
            ),
            "url": build_absolute_url(
                pBaseUrl,
                vRelativeUrl
            )
        }

    except Exception:
        logger.exception(
            "Erreur lors de l'analyse d'un livre"
        )
        raise

    rBook = vBook

    return rBook


def extract_books(pSoup, pBaseUrl):
    """
    Extrait plusieurs livres depuis une page HTML.

    :param pSoup: Page HTML contenant les livres.
    :param pBaseUrl: URL de base permettant de construire les URLs.
    :return: DataFrame contenant les livres extraits.
    """

    vBookElements = pSoup.select(
        ".product_pod"
    )

    logger.info(
        "%s livre(s) trouvé(s) dans la page",
        len(vBookElements)
    )

    vBooks = [
        extract_book(
            vBook,
            pBaseUrl
        )
        for vBook in vBookElements
    ]

    rBooks = pd.DataFrame(
        vBooks
    )

    return rBooks


def extract_next_url(pSoup, pBaseUrl):
    """
    Extrait l'URL de la page suivante.

    :param pSoup: Page HTML contenant le lien suivant.
    :param pBaseUrl: URL de base permettant de construire l'URL absolue.
    :return: URL absolue de la page suivante ou chaîne vide.
    """

    vNextElement = pSoup.select_one(
        "li.next a"
    )

    if vNextElement is None:
        rUrl = ""

    else:
        vRelativeUrl = vNextElement.get(
            "href",
            ""
        )

        rUrl = build_absolute_url(
            pBaseUrl,
            vRelativeUrl
        )

    return rUrl