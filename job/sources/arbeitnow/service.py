"""Service de scraping des offres Arbeitnow"""

import pandas as pd

from job.csv_schema import JOB_COLUMNS
from job.filter import filter_by_keyword_and_location
from job.sources.arbeitnow.client import get_jobs
from job.sources.arbeitnow.parser import parse_jobs
from utils.logger import get_logger

logger = get_logger(__name__)

# Chaque page contient plusieurs centaines d'offres.
DEFAULT_MAX_PAGES = 2


def scrape_jobs(pKeyword=None, pLocation=None, pMaxItems=None, pMaxPages=None):
    """Récupère, filtre et normalise les offres Arbeitnow.

    L'API ne propose aucune recherche : le filtrage est fait ici, avant
    la limite globale, pour ne pas conserver des offres hors sujet.
    """

    logger.info("Début du scraping Arbeitnow : %s, %s", pKeyword, pLocation)

    vMaxPages = pMaxPages if pMaxPages is not None else DEFAULT_MAX_PAGES

    vPages = []
    vCount = 0

    for vPage in range(1, vMaxPages + 1):

        vData = get_jobs(vPage)

        vJobs = filter_by_keyword_and_location(
            parse_jobs(vData.get("data") or []), pKeyword, pLocation
        )

        vPages.append(vJobs)
        vCount += len(vJobs)

        vHasNextPage = bool((vData.get("links") or {}).get("next"))
        vHasEnoughItems = pMaxItems is not None and vCount >= pMaxItems

        if not vHasNextPage or vHasEnoughItems:
            break

    vDataFrame = pd.concat(vPages, ignore_index=True)

    if pMaxItems is not None:
        vDataFrame = vDataFrame.head(pMaxItems)

    if vDataFrame.empty:
        vDataFrame = pd.DataFrame(columns=JOB_COLUMNS)

    logger.info("Scraping Arbeitnow terminé : %s offre(s)", len(vDataFrame))

    rData = vDataFrame

    return rData
