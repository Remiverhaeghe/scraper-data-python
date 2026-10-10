"""Indicateurs du tableau de bord et de l'historique, communs au bureau et au web"""

from datetime import datetime, timedelta

from config import NEW_OFFER_DAYS
from job.sources.registry import SOURCES
from storage.history_repository import get_history
from storage.job_applications import (
    count_applications_by_day,
    count_follow_ups_by_day,
)
from storage.job_offers import (
    FOLLOW_UP_STATUSES,
    count_new_offers_by_day,
    count_offers,
    count_offers_by_source,
)

RECENT_EXECUTIONS = 4

# Nombre de jours représentés par le graphique d'activité
CHART_DAYS = 14

# Séries du graphique d'activité : libellé et décompte quotidien
ACTIVITY_SERIES = {
    "new_offers": ("Nouvelles offres", count_new_offers_by_day),
    "applications": ("Candidatures", count_applications_by_day),
    "follow_ups": ("Relances", count_follow_ups_by_day),
}

# Au-delà, les sources les moins fournies sont regroupées dans « Autres »
MAX_PIE_SOURCES = 6

# Nombre d'exécutions représentées par le graphique de l'historique
EXECUTION_CHART_SIZE = 10


def load_statistics(pDatabaseFile, pNow=None):
    """Calcule les indicateurs, les dernières exécutions et l'activité par jour."""

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
        "daily_activity": {
            vName: vCount(pDatabaseFile, CHART_DAYS, vNow)
            for vName, (_, vCount) in ACTIVITY_SERIES.items()
        },
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


def get_source_shares(pDatabaseFile):
    """Retourne la part de chaque source dans les offres en base.

    Les sources au-delà des MAX_PIE_SOURCES premières sont regroupées, pour
    garder un camembert lisible.
    """

    vCounts = [
        (SOURCES[vName].label if vName in SOURCES else vName, vCount)
        for vName, vCount in count_offers_by_source(pDatabaseFile)
    ]

    if len(vCounts) > MAX_PIE_SOURCES:
        vOthers = sum(vCount for _, vCount in vCounts[MAX_PIE_SOURCES - 1 :])
        vCounts = vCounts[: MAX_PIE_SOURCES - 1] + [("Autres", vOthers)]

    vTotal = sum(vCount for _, vCount in vCounts) or 1

    rShares = [
        {"label": vLabel, "count": vCount, "percent": round(100 * vCount / vTotal)}
        for vLabel, vCount in vCounts
    ]

    return rShares


def get_execution_counts(pDatabaseFile):
    """Retourne le nombre d'offres des dernières exécutions, de la plus ancienne."""

    vEntries = list(reversed(get_history(pDatabaseFile, pLimit=EXECUTION_CHART_SIZE)))

    # Un libellé court reste lisible sous chaque barre : l'heure si toutes les
    # exécutions datent du même jour, la date sinon.
    vSameDay = len({vEntry.started_at.date() for vEntry in vEntries}) <= 1
    vFormat = "%H:%M" if vSameDay else "%d/%m"

    rCounts = [
        (vEntry.started_at.strftime(vFormat), vEntry.item_count) for vEntry in vEntries
    ]

    return rCounts
