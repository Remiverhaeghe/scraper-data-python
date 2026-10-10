"""Construction de la configuration des sources d'emploi"""

from types import SimpleNamespace

from job.config import JobScrapingConfig
from job.sources.config import SourceConfig
from job.sources.registry import SOURCES
from utils.logger import get_logger

logger = get_logger(__name__)

# Critères attendus par build_job_config, hors ligne de commande
DEFAULT_CRITERIA = {
    "max_items": None,
    "delay": 0.0,
    "timeout": 30,
    "max_pages": None,
    "keyword": None,
    "location": None,
    "max_distance_km": None,
    "contract": None,
    "min_salary": None,
    "max_salary": None,
    "remote": None,
    "min_remote_days": None,
    "metro_required": None,
    "max_metro_distance_km": None,
    "education": None,
    "skills": None,
    "missions": None,
    "exclude_keywords": None,
}


def build_search_arguments(pSources, pCriteria):
    """Construit les arguments de build_job_config pour une recherche hors CLI."""

    vUnknown = sorted(set(pCriteria) - set(DEFAULT_CRITERIA))

    if vUnknown:
        raise ValueError(f"Critère(s) de recherche inconnu(s) : {vUnknown}")

    rArguments = SimpleNamespace(**{**DEFAULT_CRITERIA, **pCriteria}, sources=pSources)

    return rArguments


def build_source_config(pSourceName, pSources):
    """Construit la configuration générique d'une source d'emploi."""

    logger.info("Construction de la configuration source : %s", pSourceName)

    vEnabled = pSourceName in pSources

    vConfig = SourceConfig(
        enabled=vEnabled,
        api_available=vEnabled,
        html_available=False,
        mode="api" if vEnabled else None,
    )

    logger.info(
        "Source %s : activée=%s, mode=%s", pSourceName, vConfig.enabled, vConfig.mode
    )

    rConfig = vConfig

    return rConfig


def build_job_config(pArguments):
    """Construit la configuration complète du scraping des offres."""

    logger.info("Début construction configuration Jobs")

    vSources = pArguments.sources or []

    for vSource in vSources:
        if not SOURCES[vSource].available:
            raise ValueError(
                f"La source {SOURCES[vSource].label} est actuellement indisponible."
            )

    logger.info("Sources sélectionnées : %s", vSources)

    vSourceConfigs = {}

    for vName, vDefinition in SOURCES.items():

        vSourceConfig = build_source_config(vName, vSources)

        if vSourceConfig.enabled:
            logger.info("Chargement de la configuration %s", vDefinition.label)

            vSourceConfig.parameters = vDefinition.load_parameters(pArguments)

        vSourceConfigs[vName] = vSourceConfig

    logger.info("Construction de JobScrapingConfig")

    vConfig = JobScrapingConfig(
        max_items=pArguments.max_items,
        delay=pArguments.delay,
        timeout=pArguments.timeout,
        max_pages=pArguments.max_pages,
        keyword=pArguments.keyword,
        location=pArguments.location,
        max_distance_km=pArguments.max_distance_km,
        contract=pArguments.contract,
        min_salary=pArguments.min_salary,
        max_salary=pArguments.max_salary,
        remote=pArguments.remote,
        min_remote_days=pArguments.min_remote_days,
        metro_required=pArguments.metro_required,
        max_metro_distance_km=pArguments.max_metro_distance_km,
        education=pArguments.education,
        skills=pArguments.skills,
        missions=pArguments.missions,
        exclude_keywords=pArguments.exclude_keywords,
        sources=vSourceConfigs,
    )

    logger.info("Validation de la configuration Jobs")

    vConfig.validate()

    logger.info("Configuration Jobs construite et validée")

    rConfig = vConfig

    return rConfig
