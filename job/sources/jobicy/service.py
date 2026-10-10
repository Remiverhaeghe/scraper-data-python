"""Service de scraping des offres Jobicy"""

import pandas as pd

from job.csv_schema import JOB_COLUMNS
from job.sources.jobicy.client import MAX_COUNT, get_jobs
from job.sources.jobicy.parser import parse_jobs
from utils.logger import get_logger

logger = get_logger(__name__)

# Offres en télétravail ouvertes aux candidats résidant en France
GEO = "france"


def scrape_jobs(pTag=None, pMaxItems=None):
    """Récupère et normalise les offres Jobicy en une seule requête."""

    logger.info("Début du scraping Jobicy : %s", pTag)

    vCount = min(MAX_COUNT, pMaxItems) if pMaxItems is not None else MAX_COUNT

    vDataFrame = parse_jobs(get_jobs(pTag, GEO, vCount))

    if vDataFrame.empty:
        vDataFrame = pd.DataFrame(columns=JOB_COLUMNS)

    logger.info("Scraping Jobicy terminé : %s offre(s)", len(vDataFrame))

    rData = vDataFrame

    return rData
