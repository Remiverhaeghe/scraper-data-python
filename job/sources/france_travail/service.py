# ============================================================================
# Service de scraping des offres France Travail
# ============================================================================

from job.sources.france_travail.client import search_jobs
from job.sources.france_travail.parser import parse_jobs
from utils.logger import get_logger

logger = get_logger(__name__)


def scrape_jobs(pConfig, pParams):
    """
    Récupère et normalise les offres France Travail.

    :param pConfig: Configuration France Travail.
    :param pParams: Paramètres de recherche.
    :return: DataFrame contenant les offres normalisées.
    """

    logger.info(
        "Début du scraping France Travail"
    )

    vData = search_jobs(
        pConfig,
        pParams
    )

    vJobs = vData.get(
        "resultats",
        []
    )

    logger.info(
        "%s offre(s) récupérée(s) depuis France Travail",
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