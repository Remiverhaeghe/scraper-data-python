"""Orchestration du traitement des offres d'emploi"""

from datetime import datetime
from dataclasses import replace

from config import DATABASE_FILE
from job.exchange_rates import get_exchange_rates
from job.filter import filter_jobs
from job.geocoding import locate_new_offers
from job.offer_purge import drop_excluded_offers, load_excluded_words
from job.settings import get_net_ratio, get_tax_rate, load_settings
from job.skill_cache import refresh_detected_skills_safely
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
        exchange_rates=get_exchange_rates(DATABASE_FILE, datetime.now()),
    )

    vScrapingResult = scrape_sources(
        vConfig, pOnProgress=pOnProgress, pCancelEvent=pCancelEvent
    )

    vScrapedAt = datetime.now()

    # Offres hors sujet déjà purgées : écartées avant l'enregistrement.
    vItems, vExcludedCount = drop_excluded_offers(
        vScrapingResult.items, load_excluded_words(DATABASE_FILE)
    )

    if vExcludedCount:
        logger.info("Offres écartées par les mots exclus : %s", vExcludedCount)

        vScrapingResult = replace(vScrapingResult, items=vItems)

    # Toutes les offres trouvées sont enregistrées, puis seul le résultat renvoyé
    # est filtré : une offre présente en base mais absente du résultat d'une
    # recherche a donc été écartée par un critère (job/filter.py).
    vSavedItems = save_offers(DATABASE_FILE, vScrapingResult.items, vScrapedAt)

    vScrapingResult = replace(vScrapingResult, items=vSavedItems)

    # Les nouvelles offres reçoivent leur position, pour le filtre de distance, par
    # lot : le planificateur place le reste. Un échec n'empêche pas d'utiliser le
    # résultat de la recherche.
    try:
        locate_new_offers(DATABASE_FILE, vScrapedAt)

    except Exception:
        logger.exception("Échec du placement des offres sur la carte")

    refresh_detected_skills_safely(DATABASE_FILE)

    vParameters = build_search_parameters(pConfig)

    if pTrigger:
        vParameters["trigger"] = pTrigger

    if vScrapingResult.rejected_count:
        vParameters["rejected"] = vScrapingResult.rejected_count
        vParameters["rejected_by_source"] = vScrapingResult.rejected_by_source

    # Offres reçues par source : une source qui n'en renvoie plus est repérée
    # par job/source_health.py.
    if vScrapingResult.source_counts:
        vParameters["source_counts"] = vScrapingResult.source_counts

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
