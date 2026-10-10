"""Construction de la configuration des sources d'emploi"""

from job.config import JobScrapingConfig
from job.sources.config import SourceConfig
from job.sources.france_travail.config import load_config as load_france_travail_config
from job.sources.greenhouse.config import load_config as load_greenhouse_config
from job.sources.lever.config import load_config as load_lever_config
from utils.logger import get_logger

logger = get_logger(__name__)


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


def build_france_travail_config(pSources, pJobConfig):
    """Construit la configuration France Travail."""

    logger.info("Début construction configuration France Travail")

    vConfig = build_source_config("france-travail", pSources)

    if vConfig.enabled:
        logger.info("Chargement de la configuration France Travail")

        vFranceTravailConfig = load_france_travail_config()

        logger.info("Configuration France Travail chargée")

        vParameters = {
            "config": vFranceTravailConfig,
            "params": build_france_travail_params(pJobConfig),
        }

        vConfig.parameters = vParameters

    logger.info("Configuration France Travail terminée")

    rConfig = vConfig

    return rConfig


def build_france_travail_params(pJobConfig):
    """Construit les paramètres de recherche France Travail.

    Seuls les paramètres dont le mapping avec l'API est actuellement
    défini dans le projet sont construits ici.
    """

    logger.info("Construction des paramètres France Travail")

    vParams = {}

    if pJobConfig.keyword:
        vParams["motsCles"] = pJobConfig.keyword

    rParams = vParams

    return rParams


def build_greenhouse_config(pSources):
    """Construit la configuration Greenhouse."""

    logger.info("Début construction configuration Greenhouse")

    vConfig = build_source_config("greenhouse", pSources)

    if vConfig.enabled:
        logger.info("Chargement de la configuration Greenhouse")

        vGreenhouseConfig = load_greenhouse_config()

        logger.info("Configuration Greenhouse chargée")

        vConfig.parameters = {"board": vGreenhouseConfig.board}

    logger.info("Configuration Greenhouse terminée")

    rConfig = vConfig

    return rConfig


def build_lever_config(pSources):
    """Construit la configuration Lever."""

    logger.info("Début construction configuration Lever")

    vConfig = build_source_config("lever", pSources)

    if vConfig.enabled:
        logger.info("Chargement de la configuration Lever")

        vLeverConfig = load_lever_config()

        logger.info("Configuration Lever chargée")

        vConfig.parameters = {"site": vLeverConfig.site}

    logger.info("Configuration Lever terminée")

    rConfig = vConfig

    return rConfig


def build_job_config(pArguments):
    """Construit la configuration complète du scraping des offres."""

    logger.info("Début construction configuration Jobs")

    vSources = pArguments.sources or []

    logger.info("Sources sélectionnées : %s", vSources)

    logger.info("Construction configuration France Travail")

    vFranceTravailConfig = build_france_travail_config(vSources, pArguments)

    logger.info("Construction configuration Greenhouse")

    vGreenhouseConfig = build_greenhouse_config(vSources)

    logger.info("Construction configuration Lever")

    vLeverConfig = build_lever_config(vSources)

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
        france_travail=vFranceTravailConfig,
        greenhouse=vGreenhouseConfig,
        lever=vLeverConfig,
    )

    logger.info("Validation de la configuration Jobs")

    vConfig.validate()

    logger.info("Configuration Jobs construite et validée")

    rConfig = vConfig

    return rConfig
