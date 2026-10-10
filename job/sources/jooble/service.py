"""Service de scraping des offres Jooble"""

import pandas as pd

from job.csv_schema import JOB_COLUMNS
from job.sources.jooble.client import search_jobs
from job.sources.jooble.parser import parse_jobs
from utils.logger import get_logger

logger = get_logger(__name__)

RESULTS_PER_PAGE = 20

DEFAULT_MAX_PAGES = 3

# Sans ville précisée, la recherche couvre la France entière.
DEFAULT_LOCATION = "France"


def build_body(pParams, pPage, pResultsPerPage):
    """Construit le corps de la requête de recherche Jooble."""

    rBody = {
        "keywords": pParams.get("keywords") or "",
        "location": pParams.get("location") or DEFAULT_LOCATION,
        "page": str(pPage),
        "ResultOnPage": str(pResultsPerPage),
    }

    if pParams.get("radius") is not None:
        rBody["radius"] = str(pParams["radius"])

    return rBody


def scrape_jobs(pConfig, pParams, pMaxItems=None, pMaxPages=None):
    """Récupère et normalise les offres Jooble."""

    logger.info("Début du scraping Jooble : %s", pParams)

    vMaxPages = pMaxPages if pMaxPages is not None else DEFAULT_MAX_PAGES

    # La taille de page reste fixe pour ne pas décaler les résultats entre pages.
    vResultsPerPage = RESULTS_PER_PAGE

    if pMaxItems is not None:
        vResultsPerPage = min(RESULTS_PER_PAGE, pMaxItems)

    vAllJobs = []

    for vPage in range(1, vMaxPages + 1):

        vData = search_jobs(pConfig, build_body(pParams, vPage, vResultsPerPage))

        vJobs = vData.get("jobs") or []

        vAllJobs.extend(vJobs)

        vIsLastPage = len(vJobs) < vResultsPerPage or len(vAllJobs) >= (
            vData.get("totalCount") or 0
        )
        vHasEnoughItems = pMaxItems is not None and len(vAllJobs) >= pMaxItems

        if vIsLastPage or vHasEnoughItems:
            break

    if pMaxItems is not None:
        vAllJobs = vAllJobs[:pMaxItems]

    vDataFrame = parse_jobs(vAllJobs)

    if vDataFrame.empty:
        vDataFrame = pd.DataFrame(columns=JOB_COLUMNS)

    logger.info("Scraping Jooble terminé : %s offre(s)", len(vDataFrame))

    rData = vDataFrame

    return rData
