# ============================================================================
# Construction de la configuration des sources d'emploi
# ============================================================================

from job.config import JobScrapingConfig
from job.sources.config import SourceConfig
from job.sources.france_travail.config import (
    load_config as load_france_travail_config
)
from job.sources.greenhouse.config import (
    load_config as load_greenhouse_config
)
from job.sources.lever.config import (
    load_config as load_lever_config
)


def build_source_config(
    pSourceName,
    pSources
):
    """
    Construit la configuration générique d'une source d'emploi.

    :param pSourceName: Nom de la source.
    :param pSources: Sources sélectionnées.
    :return: Configuration générique de la source.
    """

    vEnabled = pSourceName in pSources

    vConfig = SourceConfig(
        enabled=vEnabled,
        api_available=vEnabled,
        html_available=False,
        mode="api" if vEnabled else None
    )

    rConfig = vConfig

    return rConfig


def build_france_travail_config(pSources, pJobConfig):
    """
    Construit la configuration France Travail.

    :param pSources: Sources sélectionnées.
    :param pJobConfig: Configuration du scraping des offres.
    :return: Configuration générique France Travail.
    """

    vConfig = build_source_config(
        "france-travail",
        pSources
    )

    if vConfig.enabled:
        vFranceTravailConfig = load_france_travail_config()

        vParameters = {
            "config": vFranceTravailConfig,
            "params": build_france_travail_params(
                pJobConfig
            )
        }

        vConfig.parameters = vParameters

    rConfig = vConfig

    return rConfig


def build_france_travail_params(pJobConfig):
    """
    Construit les paramètres de recherche France Travail.

    Seuls les paramètres dont le mapping avec l'API est actuellement
    défini dans le projet sont construits ici.

    :param pJobConfig: Configuration du scraping des offres.
    :return: Paramètres de recherche France Travail.
    """

    vParams = {}

    if pJobConfig.keyword:
        vParams["motsCles"] = pJobConfig.keyword

    rParams = vParams

    return rParams


def build_greenhouse_config(pSources):
    """
    Construit la configuration Greenhouse.

    :param pSources: Sources sélectionnées.
    :return: Configuration générique Greenhouse.
    """

    vConfig = build_source_config(
        "greenhouse",
        pSources
    )

    if vConfig.enabled:
        vGreenhouseConfig = load_greenhouse_config()

        vConfig.parameters = {
            "board": vGreenhouseConfig.board
        }

    rConfig = vConfig

    return rConfig


def build_lever_config(pSources):
    """
    Construit la configuration Lever.

    :param pSources: Sources sélectionnées.
    :return: Configuration générique Lever.
    """

    vConfig = build_source_config(
        "lever",
        pSources
    )

    if vConfig.enabled:
        vLeverConfig = load_lever_config()

        vConfig.parameters = {
            "site": vLeverConfig.site
        }

    rConfig = vConfig

    return rConfig


def build_job_config(pArguments):
    """
    Construit la configuration complète du scraping des offres.

    :param pArguments: Arguments de ligne de commande.
    :return: Configuration des offres d'emploi.
    """

    vSources = pArguments.sources or []

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
        france_travail=build_france_travail_config(
            vSources,
            pArguments
        ),
        greenhouse=build_greenhouse_config(
            vSources
        ),
        lever=build_lever_config(
            vSources
        )
    )

    vConfig.validate()

    rConfig = vConfig

    return rConfig