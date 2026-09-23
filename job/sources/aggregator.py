# ============================================================================
# Agrégation des offres provenant des différentes sources
# ============================================================================

from datetime import datetime
from time import perf_counter

import pandas as pd

from job.csv_schema import JOB_COLUMNS
from job.sources.france_travail.service import (
    scrape_jobs as scrape_france_travail
)
from job.sources.greenhouse.service import (
    scrape_jobs as scrape_greenhouse
)
from job.sources.lever.service import (
    scrape_jobs as scrape_lever
)
from scraper.result import ScrapingResult
from utils.logger import get_logger


logger = get_logger(__name__)


def scrape_sources(pConfig):
    """
    Récupère et regroupe les offres des sources activées.

    :param pConfig: Configuration du scraping des offres.
    :return: Résultat de l'agrégation.
    """

    vStartedAt = datetime.now()
    vStartTime = perf_counter()

    vDataFrames = []
    vPageCount = 0

    # Vérification de la configuration
    pConfig.validate()

    # ========================================================================
    # France Travail
    # ========================================================================

    if pConfig.france_travail.enabled:
        logger.info(
            "Scraping de la source France Travail"
        )

        if pConfig.france_travail.mode != "api":
            raise ValueError(
                "Le mode sélectionné pour France Travail "
                "n'est pas encore supporté."
            )

        vParameters = pConfig.france_travail.parameters

        vConfig = vParameters.get("config")
        vParams = vParameters.get("params")

        if vConfig is None or vParams is None:
            raise ValueError(
                "La configuration France Travail est incomplète."
            )

        vDataFrame = scrape_france_travail(
            vConfig,
            vParams
        )

        vPageCount += 1

        if not vDataFrame.empty:
            vDataFrames.append(vDataFrame)

    # ========================================================================
    # Greenhouse
    # ========================================================================

    if pConfig.greenhouse.enabled:
        logger.info(
            "Scraping de la source Greenhouse"
        )

        if pConfig.greenhouse.mode != "api":
            raise ValueError(
                "Le mode sélectionné pour Greenhouse "
                "n'est pas encore supporté."
            )

        vParameters = pConfig.greenhouse.parameters
        vBoard = vParameters.get("board")

        if not vBoard:
            raise ValueError(
                "Le board Greenhouse n'est pas configuré."
            )

        vDataFrame = scrape_greenhouse(
            vBoard
        )

        vPageCount += 1

        if not vDataFrame.empty:
            vDataFrames.append(vDataFrame)

    # ========================================================================
    # Lever
    # ========================================================================

    if pConfig.lever.enabled:
        logger.info(
            "Scraping de la source Lever"
        )

        if pConfig.lever.mode != "api":
            raise ValueError(
                "Le mode sélectionné pour Lever "
                "n'est pas encore supporté."
            )

        vParameters = pConfig.lever.parameters
        vSite = vParameters.get("site")

        if not vSite:
            raise ValueError(
                "Le site Lever n'est pas configuré."
            )

        vDataFrame = scrape_lever(
            vSite
        )

        vPageCount += 1

        if not vDataFrame.empty:
            vDataFrames.append(vDataFrame)

    # ========================================================================
    # Agrégation
    # ========================================================================

    if vDataFrames:
        vItems = pd.concat(
            vDataFrames,
            ignore_index=True
        )

        vItems = vItems.reindex(
            columns=JOB_COLUMNS
        )
    else:
        vItems = pd.DataFrame(
            columns=JOB_COLUMNS
        )

    vDuration = perf_counter() - vStartTime

    vResult = ScrapingResult(
        items=vItems,
        page_count=vPageCount,
        duration_seconds=vDuration,
        started_at=vStartedAt
    )

    logger.info(
        "Agrégation terminée : %s offre(s) depuis %s source(s)",
        len(vItems),
        vPageCount
    )

    rResult = vResult

    return rResult