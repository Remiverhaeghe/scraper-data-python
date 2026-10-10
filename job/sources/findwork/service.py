"""Service de scraping des offres Findwork"""

import pandas as pd

from job.csv_schema import JOB_COLUMNS
from job.sources.findwork.client import get_jobs
from job.sources.findwork.parser import parse_jobs
from utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_MAX_PAGES = 3


def scrape_jobs(pConfig, pParams, pMaxItems=None, pMaxPages=None):
    """Récupère et normalise les offres Findwork."""

    logger.info("Début du scraping Findwork : %s", pParams)

    vMaxPages = pMaxPages if pMaxPages is not None else DEFAULT_MAX_PAGES

    vAllJobs = []

    for vPage in range(1, vMaxPages + 1):

        vData = get_jobs(pConfig, pParams, vPage)

        vAllJobs.extend(vData.get("results") or [])

        vHasNextPage = bool(vData.get("next"))
        vHasEnoughItems = pMaxItems is not None and len(vAllJobs) >= pMaxItems

        if not vHasNextPage or vHasEnoughItems:
            break

    if pMaxItems is not None:
        vAllJobs = vAllJobs[:pMaxItems]

    vDataFrame = parse_jobs(vAllJobs)

    if vDataFrame.empty:
        vDataFrame = pd.DataFrame(columns=JOB_COLUMNS)

    logger.info("Scraping Findwork terminé : %s offre(s)", len(vDataFrame))

    rData = vDataFrame

    return rData
