"""Agrégation des offres provenant des différentes sources"""

from datetime import datetime
from time import perf_counter

import pandas as pd

from job.completion import complete_offers
from job.csv_schema import JOB_COLUMNS
from job.sources.registry import SOURCES
from scraper.collection import deduplicate_dataframe, limit_dataframe
from scraper.result import ScrapingResult
from utils.logger import get_logger

logger = get_logger(__name__)


class ScrapingCancelled(Exception):
    """Signale l'arrêt d'une récupération demandé par l'utilisateur."""


def check_cancelled(pCancelEvent):
    """Lève ScrapingCancelled si l'arrêt a été demandé."""

    if pCancelEvent is not None and pCancelEvent.is_set():
        logger.info("Récupération des offres arrêtée par l'utilisateur")

        raise ScrapingCancelled("Récupération arrêtée par l'utilisateur.")


def scrape_sources(pConfig, pOnProgress=None, pCancelEvent=None):
    """Récupère et regroupe les offres des sources activées.

    pOnProgress est appelé avant chaque source avec son rang, le nombre total
    de sources et son libellé. pCancelEvent est vérifié entre deux sources :
    une requête déjà partie n'est pas interrompue.
    """

    vStartedAt = datetime.now()
    vStartTime = perf_counter()

    vDataFrames = []
    vPageCount = 0
    vErrors = []

    # Vérification de la configuration
    pConfig.validate()

    vEnabledSources = [
        (vName, vDefinition)
        for vName, vDefinition in SOURCES.items()
        if pConfig.sources.get(vName) is not None and pConfig.sources[vName].enabled
    ]

    for vIndex, (vName, vDefinition) in enumerate(vEnabledSources, start=1):

        vSourceConfig = pConfig.sources[vName]

        check_cancelled(pCancelEvent)

        if pOnProgress is not None:
            pOnProgress(vIndex, len(vEnabledSources), vDefinition.label)

        logger.info("Scraping de la source %s", vDefinition.label)

        if vSourceConfig.mode != "api":
            raise ValueError(
                f"Le mode sélectionné pour {vDefinition.label} "
                "n'est pas encore supporté."
            )

        # Une source en échec ne doit pas empêcher la récupération des autres.
        try:
            vDataFrame = vDefinition.scrape(vSourceConfig.parameters, pConfig)

        except Exception as vException:
            logger.exception("Échec de la source %s", vDefinition.label)
            vErrors.append(f"{vDefinition.label} : {vException}")
            continue

        vPageCount += 1

        if not vDataFrame.empty:
            vDataFrames.append(vDataFrame)

    check_cancelled(pCancelEvent)

    # Agrégation

    if vDataFrames:
        vItems = pd.concat(vDataFrames, ignore_index=True)

        vItems = vItems.reindex(columns=JOB_COLUMNS)

        # Création d'une clé technique uniquement pour les offres
        # possédant un identifiant fourni par leur source.
        vItems["_deduplication_key"] = pd.NA

        vHasSourceId = vItems["source_id"].notna()

        vItems.loc[vHasSourceId, "_deduplication_key"] = (
            vItems.loc[vHasSourceId, "source"].astype(str)
            + "::"
            + vItems.loc[vHasSourceId, "source_id"].astype(str)
        )

        # Suppression des doublons avant l'application de max_items.
        vItems = deduplicate_dataframe(vItems, "_deduplication_key")

        vItems = vItems.drop(columns=["_deduplication_key"])
    else:
        vItems = pd.DataFrame(columns=JOB_COLUMNS)

    vItems, vRejectedCount = complete_offers(
        vItems, pConfig.net_salary_ratio, pConfig.income_tax_rate
    )

    # Limite globale du nombre d'offres

    if pConfig.max_items is not None and len(vItems) > pConfig.max_items:
        logger.info("Limitation du résultat à %s offre(s)", pConfig.max_items)

        vItems = limit_dataframe(vItems, pConfig.max_items)

    vDuration = perf_counter() - vStartTime

    vStatus = "success"

    if vErrors:
        vStatus = "partial" if vPageCount > 0 else "error"

    vResult = ScrapingResult(
        items=vItems,
        page_count=vPageCount,
        duration_seconds=vDuration,
        started_at=vStartedAt,
        status=vStatus,
        error_message=" | ".join(vErrors) or None,
        rejected_count=vRejectedCount,
    )

    logger.info(
        "Agrégation terminée : %s offre(s) depuis %s source(s), %s source(s) en échec",
        len(vItems),
        vPageCount,
        len(vErrors),
    )

    rResult = vResult

    return rResult
