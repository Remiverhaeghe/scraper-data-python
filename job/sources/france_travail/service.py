# ============================================================================
# Service de scraping des offres France Travail
# ============================================================================

from job.sources.france_travail.client import search_jobs
from job.sources.france_travail.parser import parse_jobs
from scraper.collection import limit_dataframe
from utils.logger import get_logger

logger = get_logger(__name__)


def scrape_jobs(
    pConfig,
    pParams,
    pMaxItems=None
):
    """
    Récupère et normalise les offres France Travail.

    :param pConfig: Configuration France Travail.
    :param pParams: Paramètres de recherche.
    :param pMaxItems: Nombre maximum d'offres à conserver.
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

    if pMaxItems is not None:
        vDataFrame = limit_dataframe(
            vDataFrame,
            pMaxItems
        )

    logger.info(
        "%s offre(s) normalisée(s)",
        len(vDataFrame)
    )

    rDataFrame = vDataFrame
    return rDataFrame