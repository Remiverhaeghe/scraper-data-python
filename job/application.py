# ============================================================================
# Orchestration du traitement des offres d'emploi
# ============================================================================


from job.service import scrape_jobs
from utils.logger import get_logger


logger = get_logger(__name__)


def process_jobs(pUrl, pConfig):
    """
    Lance le traitement des offres d'emploi.

    Pour le moment, le traitement se limite au scraping.
    Le filtrage, le stockage et la détection des nouvelles offres
    seront ajoutés progressivement.

    :param pUrl: URL de départ du scraping.
    :param pConfig: Configuration du scraping.
    :return: Liste des offres récupérées.
    """

    logger.info(
        "Début du traitement des offres : %s",
        pUrl
    )

    vJobs = scrape_jobs(
        pUrl,
        pConfig
    )

    logger.info(
        "Traitement des offres terminé : %s offre(s)",
        len(vJobs)
    )

    rJobs = vJobs
    return rJobs