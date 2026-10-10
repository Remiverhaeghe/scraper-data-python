"""Service de scraping du fil Hacker News « Who is hiring? »"""

import pandas as pd

from job.csv_schema import JOB_COLUMNS
from job.filter import filter_by_keyword_and_location
from job.sources.hackernews.client import find_latest_thread_id, get_thread
from job.sources.hackernews.parser import parse_jobs
from utils.logger import get_logger

logger = get_logger(__name__)


def scrape_jobs(pKeyword=None, pLocation=None, pMaxItems=None):
    """Récupère, filtre et normalise les offres du dernier fil mensuel.

    Le fil ne propose aucune recherche : le filtrage est fait ici, avant
    la limite globale, pour ne pas conserver des offres hors sujet.
    """

    logger.info("Début du scraping Hacker News : %s, %s", pKeyword, pLocation)

    vThread = get_thread(find_latest_thread_id())

    # Seuls les commentaires de premier niveau sont des offres.
    vJobs = parse_jobs(vThread.get("children") or [])

    vDataFrame = filter_by_keyword_and_location(vJobs, pKeyword, pLocation)

    if pMaxItems is not None:
        vDataFrame = vDataFrame.head(pMaxItems)

    if vDataFrame.empty:
        vDataFrame = pd.DataFrame(columns=JOB_COLUMNS)

    logger.info(
        "Scraping Hacker News terminé : %s offre(s) sur %s",
        len(vDataFrame),
        len(vJobs),
    )

    rData = vDataFrame.reset_index(drop=True)

    return rData
