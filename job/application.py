"""Orchestration du traitement des offres d'emploi"""

from datetime import datetime
from dataclasses import replace

from config import DATABASE_FILE
from job.filter import filter_jobs
from job.sources.aggregator import scrape_sources
from scraper.history_service import record_history
from storage.job_offers import save_offers
from utils.logger import get_logger

logger = get_logger(__name__)


def process_jobs(pConfig, pOnProgress=None, pCancelEvent=None):
    """Lance le traitement des offres d'emploi.

    Le scraping produit d'abord un résultat brut provenant
    des sources activées dans la configuration.

    Les offres sont ensuite enregistrées en base, avec leurs dates de
    première et dernière récupération, avant l'enregistrement de
    l'historique et l'application des filtres. Un arrêt demandé pendant
    le scraping lève ScrapingCancelled avant tout enregistrement.
    """

    logger.info("Début du traitement des offres multi-sources")

    vScrapingResult = scrape_sources(
        pConfig, pOnProgress=pOnProgress, pCancelEvent=pCancelEvent
    )

    vScrapedAt = datetime.now()

    vSavedItems = save_offers(DATABASE_FILE, vScrapingResult.items, vScrapedAt)

    vScrapingResult = replace(vScrapingResult, items=vSavedItems)

    record_history(DATABASE_FILE, "job", "multi-source", vScrapingResult)

    vFilteredJobs = filter_jobs(vScrapingResult.items, pConfig)

    rResult = replace(vScrapingResult, items=vFilteredJobs)

    logger.info(
        "Traitement des offres terminé : %s offre(s) trouvée(s), "
        "%s offre(s) après filtrage sur %s source(s)",
        len(vScrapingResult.items),
        len(rResult.items),
        rResult.page_count,
    )

    return rResult
