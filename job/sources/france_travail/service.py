"""Service de scraping des offres France Travail"""

import pandas as pd

from job.sources.france_travail.client import search_jobs
from job.sources.france_travail.parser import parse_jobs
from scraper.collection import limit_dataframe
from utils.logger import get_logger

logger = get_logger(__name__)


FRANCE_TRAVAIL_PAGE_SIZE = 150


def scrape_jobs(pConfig, pParams, pMaxItems=None, pMaxPages=None):
    """Récupère et normalise les offres France Travail."""

    logger.info("Début du scraping France Travail")

    vAllDataFrames = []
    vStart = 0
    vPageCount = 0
    vTotalItems = 0
    vHasResults = True

    while vHasResults:

        if pMaxPages is not None and vPageCount >= pMaxPages:
            break

        if pMaxItems is not None and vTotalItems >= pMaxItems:
            break

        if pMaxItems is not None:
            vRemainingItems = pMaxItems - vTotalItems

            vPageSize = min(FRANCE_TRAVAIL_PAGE_SIZE, vRemainingItems)
        else:
            vPageSize = FRANCE_TRAVAIL_PAGE_SIZE

        vEnd = vStart + vPageSize - 1

        vRange = f"{vStart}-{vEnd}"

        logger.info(
            "Récupération de la page France Travail %s (range=%s)",
            vPageCount + 1,
            vRange,
        )

        vData = search_jobs(pConfig, pParams, pRange=vRange)

        vJobs = vData.get("resultats", [])

        vPageCount += 1

        logger.info("%s offre(s) récupérée(s) sur la page %s", len(vJobs), vPageCount)

        if not vJobs:
            vHasResults = False
        else:
            vDataFrame = parse_jobs(vJobs)

            vAllDataFrames.append(vDataFrame)

            vTotalItems += len(vJobs)
            vStart += len(vJobs)

            if len(vJobs) < vPageSize:
                vHasResults = False

    if vAllDataFrames:
        vDataFrame = pd.concat(vAllDataFrames, ignore_index=True)
    else:
        vDataFrame = parse_jobs([])

    if pMaxItems is not None:
        vDataFrame = limit_dataframe(vDataFrame, pMaxItems)

    logger.info(
        "%s offre(s) normalisée(s) depuis %s page(s)", len(vDataFrame), vPageCount
    )

    rDataFrame = vDataFrame

    return rDataFrame
