# ============================================================================
# Gestion générique de la pagination du scraper
# ============================================================================


import time
from datetime import datetime

import pandas as pd

from scraper.collection import (
    deduplicate_dataframe,
    has_reached_limit
)
from scraper.result import ScrapingResult
from utils.logger import get_logger


logger = get_logger(__name__)


def scrape_paginated(
    pUrl,
    pConfig,
    pFetchPage,
    pParseHtml,
    pExtractItems,
    pExtractNextUrl,
    pDeduplicateColumn=None
):
    """
    Scrape plusieurs pages et retourne les données sous forme de DataFrame.

    :param pUrl: URL de départ.
    :param pConfig: Configuration du scraping.
    :param pFetchPage: Fonction de récupération HTML.
    :param pParseHtml: Fonction d'analyse HTML.
    :param pExtractItems: Fonction d'extraction des éléments.
    :param pExtractNextUrl: Fonction d'extraction de la page suivante.
    :param pDeduplicateColumn: Colonne utilisée pour supprimer les doublons.
    :return: Résultat du scraping.
    """

    vStartTime = time.perf_counter()
    vStartedAt = datetime.now()

    vDataFrame = pd.DataFrame()
    vCurrentUrl = pUrl
    vPageCount = 0
    vStatus = "success"
    vErrorMessage = None

    try:
        while vCurrentUrl:

            if (
                pConfig.max_pages is not None
                and vPageCount >= pConfig.max_pages
            ):
                break

            if has_reached_limit(
                vDataFrame,
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

            vPageDataFrame = pExtractItems(
                vSoup,
                vCurrentUrl
            )

            if not vPageDataFrame.empty:

                if vDataFrame.empty:
                    vDataFrame = vPageDataFrame.copy()
                else:
                    vDataFrame = pd.concat(
                        [
                            vDataFrame,
                            vPageDataFrame
                        ],
                        ignore_index=True
                    )

            if (
                pConfig.avoid_duplicates
                and pDeduplicateColumn is not None
                and pDeduplicateColumn in vDataFrame.columns
            ):
                vDataFrame = deduplicate_dataframe(
                    vDataFrame,
                    pDeduplicateColumn
                )

            if has_reached_limit(
                vDataFrame,
                pConfig.max_items
            ):
                vDataFrame = vDataFrame.iloc[
                    :pConfig.max_items
                ].reset_index(
                    drop=True
                )

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

    vDuration = (
        time.perf_counter()
        - vStartTime
    )

    rResult = ScrapingResult(
        items=vDataFrame,
        page_count=vPageCount,
        duration_seconds=vDuration,
        started_at=vStartedAt,
        status=vStatus,
        error_message=vErrorMessage
    )

    return rResult