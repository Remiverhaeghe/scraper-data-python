# ============================================================================
# Orchestration du traitement des offres d'emploi
# ============================================================================


from dataclasses import replace

from config import DATABASE_FILE
from job.filter import filter_jobs
from job.service import scrape_jobs
from scraper.history_service import record_history
from utils.logger import get_logger


logger = get_logger(__name__)


def process_jobs(pUrl, pConfig):
    """
    Lance le traitement des offres d'emploi.

    Le scraping produit d'abord un résultat brut.
    Ce résultat est enregistré dans l'historique avant
    l'application des filtres de recherche.

    :param pUrl: URL de départ du scraping.
    :param pConfig: Configuration du scraping et des filtres.
    :return: Résultat du scraping après filtrage.
    """

    logger.info(
        "Début du traitement des offres : %s",
        pUrl
    )

    vScrapingResult = scrape_jobs(
        pUrl,
        pConfig
    )

    record_history(
        DATABASE_FILE,
        "job",
        pUrl,
        vScrapingResult
    )

    vFilteredJobs = filter_jobs(
        vScrapingResult.items,
        pConfig
    )

    rResult = replace(
        vScrapingResult,
        items=vFilteredJobs
    )

    logger.info(
        "Traitement des offres terminé : %s offre(s) trouvée(s), "
        "%s offre(s) après filtrage sur %s page(s)",
        len(vScrapingResult.items),
        len(rResult.items),
        rResult.page_count
    )

    return rResult