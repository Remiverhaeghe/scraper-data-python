"""Service de scraping des offres Adzuna"""

import pandas as pd

from job.csv_schema import JOB_COLUMNS
from job.sources.adzuna.client import RESULTS_PER_PAGE, search_jobs
from job.sources.adzuna.parser import parse_jobs
from utils.logger import get_logger

logger = get_logger(__name__)

# Plafond appliqué sans max_pages pour préserver le quota de 250 requêtes par jour
DEFAULT_MAX_PAGES = 5


def scrape_jobs(pConfig, pParams, pMaxItems=None, pMaxPages=None):
    """Récupère et normalise les offres Adzuna."""

    logger.info("Début du scraping Adzuna : %s", pParams)

    vMaxPages = pMaxPages if pMaxPages is not None else DEFAULT_MAX_PAGES

    # La taille de page reste fixe : la changer en cours de route décalerait
    # les résultats entre deux pages.
    vResultsPerPage = RESULTS_PER_PAGE

    if pMaxItems is not None:
        vResultsPerPage = min(RESULTS_PER_PAGE, pMaxItems)

    vAllJobs = []

    for vPage in range(1, vMaxPages + 1):

        vData = search_jobs(pConfig, pParams, vPage, vResultsPerPage)

        vJobs = vData.get("results") or []

        vAllJobs.extend(vJobs)

        vIsLastPage = len(vJobs) < vResultsPerPage
        vHasEnoughItems = pMaxItems is not None and len(vAllJobs) >= pMaxItems

        if vIsLastPage or vHasEnoughItems:
            break

    if pMaxItems is not None:
        vAllJobs = vAllJobs[:pMaxItems]

    vDataFrame = parse_jobs(vAllJobs)

    if vDataFrame.empty:
        vDataFrame = pd.DataFrame(columns=JOB_COLUMNS)

    logger.info("Scraping Adzuna terminé : %s offre(s)", len(vDataFrame))

    rData = vDataFrame

    return rData
