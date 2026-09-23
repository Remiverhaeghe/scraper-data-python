# ============================================================================
# Service de récupération des offres Greenhouse
# ============================================================================

from job.sources.greenhouse.client import get_jobs
from job.sources.greenhouse.parser import parse_jobs
from utils.logger import get_logger

logger = get_logger(__name__)


def scrape_jobs(pBoardToken):
    """
    Récupère et normalise les offres d'un board Greenhouse.

    :param pBoardToken: Identifiant public du board.
    :return: DataFrame contenant les offres normalisées.
    """

    logger.info(
        "Début du scraping Greenhouse"
    )

    vData = get_jobs(
        pBoardToken
    )

    vJobs = vData.get(
        "jobs",
        []
    )

    logger.info(
        "%s offre(s) récupérée(s) depuis Greenhouse",
        len(vJobs)
    )

    vDataFrame = parse_jobs(
        vJobs
    )

    logger.info(
        "%s offre(s) normalisée(s)",
        len(vDataFrame)
    )

    rDataFrame = vDataFrame
    return rDataFrame