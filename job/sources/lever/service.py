# ============================================================================
# Service de scraping des offres Lever
# ============================================================================

import pandas as pd

from job.csv_schema import JOB_COLUMNS
from job.sources.lever.client import get_jobs
from job.sources.lever.parser import parse_jobs
from utils.logger import get_logger


logger = get_logger(__name__)


def scrape_jobs(
    pSite,
    pLimit=100,
    pMaxItems=None
):
    """
    Récupère et normalise les offres d'un site Lever.

    :param pSite: Identifiant du site Lever.
    :param pLimit: Nombre maximum d'offres par appel.
    :param pMaxItems: Nombre maximum d'offres à récupérer.
    :return: DataFrame des offres.
    """

    logger.info(
        "Début du scraping Lever : %s",
        pSite
    )

    vAllJobs = []
    vSkip = 0
    vHasResults = True

    while vHasResults:

        # Calcul du nombre d'offres restant à récupérer.
        if pMaxItems is not None:
            vRemainingItems = pMaxItems - len(vAllJobs)

            if vRemainingItems <= 0:
                vHasResults = False
                continue

            vRequestLimit = min(
                pLimit,
                vRemainingItems
            )
        else:
            vRequestLimit = pLimit

        vJobs = get_jobs(
            pSite,
            pLimit=vRequestLimit,
            pSkip=vSkip
        )

        if not vJobs:
            vHasResults = False
        else:
            vAllJobs.extend(vJobs)

            if len(vJobs) < vRequestLimit:
                vHasResults = False
            else:
                vSkip += len(vJobs)

    vDataFrame = parse_jobs(
        vAllJobs
    )

    if vDataFrame.empty:
        vDataFrame = pd.DataFrame(
            columns=JOB_COLUMNS
        )

    logger.info(
        "Scraping Lever terminé : %s offres",
        len(vDataFrame)
    )

    rData = vDataFrame

    return rData