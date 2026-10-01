# ============================================================================
# Orchestration du traitement des offres d'emploi
# ============================================================================

from dataclasses import replace

from config import DATABASE_FILE
from job.filter import filter_jobs
from job.sources.aggregator import scrape_sources
from scraper.history_service import record_history
from utils.logger import get_logger


logger = get_logger(__name__)


def process_jobs(pConfig):
    """
    Lance le traitement des offres d'emploi.

    Le scraping produit d'abord un résultat brut provenant
    des sources activées dans la configuration.
    Ce résultat est enregistré dans l'historique avant
    l'application des filtres de recherche.

    :param pConfig: Configuration du scraping et des filtres.
    :return: Résultat du scraping après filtrage.
    """

    logger.info(
        "Début du traitement des offres multi-sources"
    )

    vScrapingResult = scrape_sources(
        pConfig
    )

    record_history(
        DATABASE_FILE,
        "job",
        "multi-source",
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
        "%s offre(s) après filtrage sur %s source(s)",
        len(vScrapingResult.items),
        len(rResult.items),
        rResult.page_count
    )

    return rResult