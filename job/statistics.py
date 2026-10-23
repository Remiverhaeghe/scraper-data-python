"""Indicateurs du tableau de bord et de l'historique, communs au bureau et au web"""

from datetime import datetime, timedelta

from job.preparation import score_offers
from job.presentation import get_source_label, prepare_offer
from job.profile import load_profile
from job.settings import load_settings
from job.similar_offers import find_similar_offers
from job.sources.registry import SOURCES
from storage.history_repository import get_history
from storage.job_applications import (
    count_applied_since,
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

# Comparaison des sources : période observée et score d'une offre intéressante
SOURCE_COMPARISON_DAYS = 30
GOOD_MATCH_SCORE = 50

# Offres retenues (suivies au-delà d'un simple coup d'œil) et candidatures envoyées
KEPT_STATUSES = ("INTERESTED", "APPLIED", "INTERVIEW", "REJECTED", "ACCEPTED")
SENT_STATUSES = ("APPLIED", "INTERVIEW", "REJECTED", "ACCEPTED")


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
        "week_goal": get_week_goal(pDatabaseFile, vNow),
        "upcoming_follow_ups": get_upcoming_follow_ups(
            pDatabaseFile, DASHBOARD_LIST_SIZE
        ),
        "latest_offers": [
            prepare_offer(vOffer, vNow - timedelta(days=vNewOfferDays))
            for vOffer in get_offers(
                pDatabaseFile, pLimit=DASHBOARD_LIST_SIZE, pHideIgnored=True
            ).to_dict("records")
        ],
        "similar_offers": find_similar_offers(pDatabaseFile, vNow, DASHBOARD_LIST_SIZE),
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
        (get_source_label(vName), vCount)
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


def get_week_goal(pDatabaseFile, pNow):
    """Retourne l'objectif de candidatures de la semaine et sa progression.

    La semaine commence le lundi à minuit ; sans objectif, share vaut None.
    """

    vGoal = load_settings(pDatabaseFile)["weekly_application_goal"]
    vMonday = (pNow - timedelta(days=pNow.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    vSent = count_applied_since(pDatabaseFile, vMonday)

    rGoal = {
        "goal": vGoal,
        "sent": vSent,
        "share": min(round(100 * vSent / vGoal), 100) if vGoal else None,
    }

    return rGoal


def compare_sources(pDatabaseFile, pNow, pDays=SOURCE_COMPARISON_DAYS):
    """Retourne, par source, les offres découvertes sur la période et leur intérêt.

    Une source utile apporte des offres proches du profil, retenues ou menant à
    une candidature, pas seulement beaucoup d'offres. Tri : les plus utiles en tête.
    """

    vOffers = get_offers(
        pDatabaseFile, pSeenSince=pNow - timedelta(days=pDays)
    ).to_dict("records")
    score_offers(vOffers, load_profile(pDatabaseFile))

    vRows = {}

    for vOffer in vOffers:
        vRow = vRows.setdefault(
            vOffer["source"],
            {
                "source": vOffer["source"],
                "label": get_source_label(vOffer["source"]),
                "offers": 0,
                "good": 0,
                "kept": 0,
                "sent": 0,
                "ignored": 0,
                "scores": [],
            },
        )
        vStatus = vOffer.get("application_status")
        vScore = vOffer["match_score"]

        vRow["offers"] += 1
        vRow["good"] += vScore is not None and vScore >= GOOD_MATCH_SCORE
        vRow["kept"] += vStatus in KEPT_STATUSES
        vRow["sent"] += vStatus in SENT_STATUSES
        vRow["ignored"] += vStatus == "IGNORED"

        if vScore is not None:
            vRow["scores"].append(vScore)

    rComparison = []

    for vRow in vRows.values():
        vScores = vRow.pop("scores")
        vRow["good_rate"] = round(100 * vRow["good"] / vRow["offers"])
        vRow["average_score"] = round(sum(vScores) / len(vScores)) if vScores else None
        rComparison.append(vRow)

    rComparison.sort(
        key=lambda pRow: (
            -pRow["sent"],
            -pRow["kept"],
            -pRow["good"],
            -pRow["offers"],
            pRow["label"],
        )
    )

    return rComparison


# En-têtes du tableau de comparaison, dans l'ordre de build_source_cells
SOURCE_COMPARISON_COLUMNS = (
    "Source",
    "Offres",
    f"Score ≥ {GOOD_MATCH_SCORE} %",
    "Retenues",
    "Candidatures",
    "Ignorées",
    "Score moyen",
)


def build_source_cells(pRow):
    """Met en texte une ligne de compare_sources, pour le bureau comme le web."""

    rCells = [
        pRow["label"],
        str(pRow["offers"]),
        f"{pRow['good']} ({pRow['good_rate']} %)",
        str(pRow["kept"]),
        str(pRow["sent"]),
        str(pRow["ignored"]),
        "—" if pRow["average_score"] is None else f"{pRow['average_score']} %",
    ]

    return rCells


# Au-dessous, une source a trop peu d'offres pour être jugée
MIN_JUDGED_OFFERS = 20


def describe_useless_sources(pComparison):
    """Retourne le conseil de décocher les sources sans offre utile, ou "".

    Une source n'est jugée qu'avec assez d'offres et un profil renseigné : sans
    compétences, aucune offre ne peut atteindre le score attendu.
    """

    if all(vRow["average_score"] is None for vRow in pComparison):
        return ""

    vUseless = [
        f"{vRow['label']} ({vRow['offers']} offres)"
        for vRow in pComparison
        if vRow["offers"] >= MIN_JUDGED_OFFERS
        and not (vRow["good"] or vRow["kept"] or vRow["sent"])
    ]

    rText = (
        "À envisager de décocher, aucune offre à "
        f"{GOOD_MATCH_SCORE} % ni retenue en {SOURCE_COMPARISON_DAYS} jours : "
        + ", ".join(vUseless)
        if vUseless
        else ""
    )

    return rText
