# ============================================================================
# Orchestration du traitement des offres d'emploi
# ============================================================================


from config import DATABASE_FILE
from job.service import scrape_jobs
from scraper.history_service import record_history
from utils.logger import get_logger


logger = get_logger(__name__)


def process_jobs(pUrl, pConfig):
    """
    Lance le traitement des offres d'emploi.

    Pour le moment, le traitement se limite au scraping et à
    l'enregistrement de l'exécution dans l'historique.

    :param pUrl: URL de départ du scraping.
    :param pConfig: Configuration du scraping.
    :return: Résultat du scraping.
    """

    logger.info(
        "Début du traitement des offres : %s",
        pUrl
    )

    rResult = scrape_jobs(
        pUrl,
        pConfig
    )

    record_history(
        DATABASE_FILE,
        "job",
        pUrl,
        rResult
    )

    logger.info(
        "Traitement des offres terminé : %s offre(s) sur %s page(s)",
        len(rResult.items),
        rResult.page_count
    )

    return rResult