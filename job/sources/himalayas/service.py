"""Service de scraping des offres Himalayas"""

import pandas as pd

from job.csv_schema import JOB_COLUMNS
from job.sources.himalayas.client import search_jobs
from job.sources.himalayas.parser import parse_jobs
from utils.logger import get_logger

logger = get_logger(__name__)

# Offres en télétravail ouvertes aux candidats résidant en France
COUNTRY = "France"

# Chaque page ne contient que 20 offres et l'API limite le nombre de requêtes.
DEFAULT_MAX_PAGES = 3


def scrape_jobs(pQuery=None, pMaxItems=None, pMaxPages=None):
    """Récupère et normalise les offres Himalayas."""

    logger.info("Début du scraping Himalayas : %s", pQuery)

    vMaxPages = pMaxPages if pMaxPages is not None else DEFAULT_MAX_PAGES

    vAllJobs = []

    for vPage in range(1, vMaxPages + 1):

        vData = search_jobs(pQuery, COUNTRY, vPage)

        vJobs = vData.get("jobs") or []

        vAllJobs.extend(vJobs)

        vIsLastPage = not vJobs or len(vAllJobs) >= (vData.get("totalCount") or 0)
        vHasEnoughItems = pMaxItems is not None and len(vAllJobs) >= pMaxItems

        if vIsLastPage or vHasEnoughItems:
            break

    if pMaxItems is not None:
        vAllJobs = vAllJobs[:pMaxItems]

    vDataFrame = parse_jobs(vAllJobs)

    if vDataFrame.empty:
        vDataFrame = pd.DataFrame(columns=JOB_COLUMNS)

    logger.info("Scraping Himalayas terminé : %s offre(s)", len(vDataFrame))

    rData = vDataFrame

    return rData
