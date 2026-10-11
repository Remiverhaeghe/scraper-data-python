"""Indicateurs du tableau de bord et de l'historique, communs au bureau et au web"""

from datetime import datetime, timedelta

from job.settings import load_settings
from job.sources.registry import SOURCES
from storage.history_repository import get_history
from job.presentation import prepare_offer
from storage.job_applications import (
    count_applications_by_day,
    count_follow_ups_by_day,
    get_upcoming_follow_ups,
)
from storage.job_offers import (
    FOLLOW_UP_STATUSES,
    count_new_offers_by_day,
    count_offers,
    count_offers_by_contract,
    count_offers_by_source,
    get_offers,
)

RECENT_EXECUTIONS = 3

# Nombre de lignes des listes « Relances à venir » et « Dernières offres »
DASHBOARD_LIST_SIZE = 4

# Libellés des axes horizontal et vertical, communs au bureau et au web
ACTIVITY_AXES = ("Jour", "Nombre par jour")
EXECUTION_AXES = ("Exécution", "Offres récupérées")

# Texte affiché à la place d'un graphique sans aucune valeur
EMPTY_CHART_TEXT = "Aucune activité pour le moment"

# Nombre de jours représentés au plus par le graphique d'activité
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
    vNewOfferDays = load_settings(pDatabaseFile)["new_offer_days"]

    rStatistics = {
        "offers": count_offers(pDatabaseFile, pHideIgnored=True),
        "new_offers": count_offers(
            pDatabaseFile,
            pSeenSince=vNow - timedelta(days=vNewOfferDays),
            pHideIgnored=True,
        ),
        "applications": sum(
            count_offers(pDatabaseFile, pStatus=vStatus)
            for vStatus in FOLLOW_UP_STATUSES
        ),
        "follow_ups": count_offers(pDatabaseFile, pFollowUpBefore=vNow),
        "new_offer_days": vNewOfferDays,
        "upcoming_follow_ups": get_upcoming_follow_ups(
            pDatabaseFile, DASHBOARD_LIST_SIZE
        ),
        "latest_offers": [
            prepare_offer(vOffer, vNow - timedelta(days=vNewOfferDays))
            for vOffer in get_offers(
                pDatabaseFile, pLimit=DASHBOARD_LIST_SIZE, pHideIgnored=True
            ).to_dict("records")
        ],
        "executions": get_history(pDatabaseFile, pLimit=RECENT_EXECUTIONS),
        "daily_activity": trim_leading_empty_days(
            {
                vName: vCount(pDatabaseFile, CHART_DAYS, vNow)
                for vName, (_, vCount) in ACTIVITY_SERIES.items()
            }
        ),
    }

    return rStatistics


def trim_leading_empty_days(pDailyActivity):
    """Fait démarrer l'activité au premier jour non vide, ou au dernier jour.

    Sans cela, une base récente afficherait surtout des jours vides avant
    les premières offres.
    """

    vSeries = list(pDailyActivity.values())
    vDayCount = len(vSeries[0]) if vSeries else 0

    vFirstActiveDay = next(
        (
            vIndex
            for vIndex in range(vDayCount)
            if any(vCounts[vIndex][1] for vCounts in vSeries)
        ),
        vDayCount,
    )

    vStart = max(min(vFirstActiveDay, vDayCount - 1), 0)

    rDailyActivity = {
        vName: vCounts[vStart:] for vName, vCounts in pDailyActivity.items()
    }

    return rDailyActivity


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

    rShares = build_shares(vCounts)

    return rShares


def build_shares(pCounts):
    """Calcule la part de chaque libellé, en pourcentage du total."""

    vTotal = sum(vCount for _, vCount in pCounts) or 1

    rShares = [
        {"label": vLabel, "count": vCount, "percent": round(100 * vCount / vTotal)}
        for vLabel, vCount in pCounts
    ]

    return rShares


def get_contract_shares(pDatabaseFile):
    """Retourne la part de chaque type de contrat dans les offres en base."""

    rShares = build_shares(
        [
            (vContract or "Non précisé", vCount)
            for vContract, vCount in count_offers_by_contract(pDatabaseFile)
        ]
    )

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
