"""Indicateurs du tableau de bord, communs au bureau et au web"""

from datetime import datetime, timedelta

from config import NEW_OFFER_DAYS
from job.sources.registry import SOURCES
from storage.history_repository import get_history
from storage.job_offers import (
    FOLLOW_UP_STATUSES,
    count_new_offers_by_day,
    count_offers,
)

RECENT_EXECUTIONS = 4

# Nombre de jours représentés par le graphique des nouvelles offres
CHART_DAYS = 14


def load_statistics(pDatabaseFile, pNow=None):
    """Calcule les indicateurs, les dernières exécutions et les offres par jour."""

    vNow = pNow if pNow is not None else datetime.now()

    rStatistics = {
        "offers": count_offers(pDatabaseFile, pHideIgnored=True),
        "new_offers": count_offers(
            pDatabaseFile,
            pSeenSince=vNow - timedelta(days=NEW_OFFER_DAYS),
            pHideIgnored=True,
        ),
        "applications": sum(
            count_offers(pDatabaseFile, pStatus=vStatus)
            for vStatus in FOLLOW_UP_STATUSES
        ),
        "follow_ups": count_offers(pDatabaseFile, pFollowUpBefore=vNow),
        "executions": get_history(pDatabaseFile, pLimit=RECENT_EXECUTIONS),
        "daily_new_offers": count_new_offers_by_day(pDatabaseFile, CHART_DAYS, vNow),
    }

    return rStatistics


def count_ready_sources():
    """Compte les sources utilisables, c'est-à-dire disponibles et configurées."""

    rCount = sum(
        1
        for vDefinition in SOURCES.values()
        if vDefinition.get_unavailability_reason() is None
    )

    return rCount
