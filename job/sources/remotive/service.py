"""Service de scraping des offres Remotive"""

from datetime import UTC, datetime, timedelta

import pandas as pd

from job.csv_schema import JOB_COLUMNS
from job.sources.remotive.client import get_jobs
from job.sources.remotive.parser import parse_jobs
from utils.logger import get_logger

logger = get_logger(__name__)

# Les conditions de Remotive imposent d'attendre 24 heures avant d'afficher une offre.
PUBLICATION_DELAY = timedelta(hours=24)

# Sans mot-clé, l'API renverrait l'ensemble des offres publiées.
DEFAULT_LIMIT = 200


def is_publishable(pJob, pNow):
    """Indique si le délai de publication imposé par Remotive est écoulé."""

    rIsPublishable = False

    try:
        vPublishedAt = datetime.fromisoformat(pJob.get("publication_date") or "")
        rIsPublishable = vPublishedAt <= pNow - PUBLICATION_DELAY

    except ValueError:
        logger.warning("Date de publication Remotive invalide : %s", pJob.get("id"))

    return rIsPublishable


def scrape_jobs(pSearch=None, pMaxItems=None, pNow=None):
    """Récupère et normalise les offres Remotive."""

    logger.info("Début du scraping Remotive : %s", pSearch)

    # Les dates Remotive sont en UTC sans fuseau explicite.
    vNow = pNow or datetime.now(UTC).replace(tzinfo=None)

    vJobs = get_jobs(pSearch, pLimit=None if pSearch else DEFAULT_LIMIT)

    vPublishableJobs = [vJob for vJob in vJobs if is_publishable(vJob, vNow)]

    if len(vPublishableJobs) < len(vJobs):
        logger.info(
            "%s offre(s) Remotive de moins de 24 h écartée(s)",
            len(vJobs) - len(vPublishableJobs),
        )

    if pMaxItems is not None:
        vPublishableJobs = vPublishableJobs[:pMaxItems]

    vDataFrame = parse_jobs(vPublishableJobs)

    if vDataFrame.empty:
        vDataFrame = pd.DataFrame(columns=JOB_COLUMNS)

    logger.info("Scraping Remotive terminé : %s offre(s)", len(vDataFrame))

    rData = vDataFrame

    return rData
