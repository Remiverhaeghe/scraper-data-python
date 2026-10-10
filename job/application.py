"""Orchestration du traitement des offres d'emploi"""

from datetime import datetime
from dataclasses import replace

from config import DATABASE_FILE
from job.filter import filter_jobs
from job.settings import get_net_ratio, get_tax_rate, load_settings
from job.sources.aggregator import scrape_sources
from scraper.history_service import record_history
from storage.job_offers import save_offers
from utils.logger import get_logger

logger = get_logger(__name__)

# Critères de recherche conservés dans l'historique lorsqu'ils sont renseignés
HISTORY_CRITERIA = (
    "keyword",
    "location",
    "contract",
    "min_salary",
    "max_salary",
    "remote",
    "skills",
    "exclude_keywords",
)


def build_search_parameters(pConfig):
    """Décrit une recherche pour l'historique : critères renseignés et sources."""

    vParameters = {
        vName: getattr(pConfig, vName)
        for vName in HISTORY_CRITERIA
        if getattr(pConfig, vName) is not None
    }

    vParameters["sources"] = [
        vName
        for vName, vSourceConfig in pConfig.sources.items()
        if vSourceConfig.enabled
    ]

    rParameters = vParameters

    return rParameters


def process_jobs(pConfig, pOnProgress=None, pCancelEvent=None, pTrigger=None):
    """Lance le traitement des offres d'emploi.

    Le scraping produit d'abord un résultat brut provenant
    des sources activées dans la configuration.

    Les offres sont ensuite enregistrées en base, avec leurs dates de
    première et dernière récupération, avant l'enregistrement de
    l'historique et l'application des filtres. Un arrêt demandé pendant
    le scraping lève ScrapingCancelled avant tout enregistrement. pTrigger
    indique dans l'historique ce qui a déclenché une recherche automatique.
    """

    logger.info("Début du traitement des offres multi-sources")

    # Les réglages de calcul enregistrés depuis les interfaces s'appliquent ici.
    vSettings = load_settings(DATABASE_FILE)

    vConfig = replace(
        pConfig,
        net_salary_ratio=get_net_ratio(vSettings),
        income_tax_rate=get_tax_rate(vSettings),
    )

    vScrapingResult = scrape_sources(
        vConfig, pOnProgress=pOnProgress, pCancelEvent=pCancelEvent
    )

    vScrapedAt = datetime.now()

    vSavedItems = save_offers(DATABASE_FILE, vScrapingResult.items, vScrapedAt)

    vScrapingResult = replace(vScrapingResult, items=vSavedItems)

    vParameters = build_search_parameters(pConfig)

    if pTrigger:
        vParameters["trigger"] = pTrigger

    record_history(
        DATABASE_FILE, "job", "multi-source", vScrapingResult, pParameters=vParameters
    )

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
