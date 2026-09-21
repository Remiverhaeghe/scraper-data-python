# ============================================================================
# Gestion commune de la pagination des scrapers
# ============================================================================


import time
from datetime import datetime

from scraper.collection import has_reached_limit
from scraper.result import ScrapingResult
from utils.logger import get_logger


logger = get_logger(__name__)


def scrape_paginated(
    pUrl,
    pConfig,
    pFetchPage,
    pParseHtml,
    pExtractItems,
    pExtractNextUrl
):
    """
    Parcourt plusieurs pages et récupère les éléments présents sur chaque page.

    :param pUrl: URL de départ.
    :param pConfig: Configuration commune du scraping.
    :param pFetchPage: Fonction permettant de récupérer une page.
    :param pParseHtml: Fonction permettant de parser le HTML.
    :param pExtractItems: Fonction permettant d'extraire les éléments.
    :param pExtractNextUrl: Fonction permettant de récupérer l'URL suivante.
    :return: Résultat du scraping paginé.
    """

    vStartTime = time.perf_counter()
    vStartedAt = datetime.now()

    vItems = []
    vCurrentUrl = pUrl
    vPageCount = 0
    vStatus = "success"
    vErrorMessage = None

    try:
        while vCurrentUrl:
            # Vérification du nombre maximum de pages
            if (
                pConfig.max_pages is not None
                and vPageCount >= pConfig.max_pages
            ):
                break

            # Vérification du nombre maximum d'éléments
            if has_reached_limit(
                vItems,
                pConfig.max_items
            ):
                break

            vPageCount += 1

            logger.info(
                "Traitement de la page %s : %s",
                vPageCount,
                vCurrentUrl
            )

            vHtml = pFetchPage(
                vCurrentUrl,
                pConfig
            )

            vSoup = pParseHtml(
                vHtml
            )

            vItems.extend(
                pExtractItems(
                    vSoup,
                    vCurrentUrl
                )
            )

            # Limitation du nombre maximum d'éléments
            if has_reached_limit(
                vItems,
                pConfig.max_items
            ):
                vItems = vItems[
                    :pConfig.max_items
                ]
                break

            vCurrentUrl = pExtractNextUrl(
                vSoup,
                vCurrentUrl
            )

    except Exception as vException:
        vStatus = "error"
        vErrorMessage = str(vException)

        logger.exception(
            "Erreur pendant le scraping à la page %s : %s",
            vPageCount,
            vException
        )

    vDuration = time.perf_counter() - vStartTime

    rResult = ScrapingResult(
        items=vItems,
        page_count=vPageCount,
        duration_seconds=vDuration,
        started_at=vStartedAt,
        status=vStatus,
        error_message=vErrorMessage
    )

    return rResult