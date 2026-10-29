"""Indicateurs du tableau de bord et de l'historique, communs au bureau et au web"""

from datetime import datetime, timedelta

from job.companies import find_preferred_offers
from job.followed_availability import list_withdrawn_offers
from job.filter import matches_keyword, matches_location
from job.preparation import score_offers
from job.presentation import clean_missing_values, get_source_label, prepare_offer
from job.profile import load_profile
from job.settings import load_settings
from job.similar_offers import find_similar_offers
from job.sources.registry import SOURCES
from storage.history_repository import get_history
from storage.job_applications import (
    count_applied_since,
    count_applications_by_day,
    count_interviews_by_source,
    count_follow_ups_by_day,
    count_responses_by_day,
    get_upcoming_follow_ups,
    get_waiting_interests,
)
from storage.job_offers import (
    FOLLOW_UP_STATUSES,
    count_new_offers_by_day,
    count_offers,
    count_offers_by_contract,
    count_offers_by_source,
    get_offers,
)
from storage.saved_searches import get_saved_searches
from storage.settings_repository import load_json_setting, save_json_setting
from utils.logger import get_logger

logger = get_logger(__name__)

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

# Le bilan de la semaine ajoute les réponses reçues, absentes du graphique.
WEEK_SERIES = {
    **ACTIVITY_SERIES,
    "responses": ("Réponses reçues", count_responses_by_day),
}

WEEK_DAYS = 7

# Bilan mensuel de la page Historique : 30 derniers jours et 30 précédents
MONTH_DAYS = 30

# Au-delà, les sources les moins fournies sont regroupées dans « Autres »
MAX_PIE_SOURCES = 6

# Nombre d'exécutions représentées par le graphique de l'historique
EXECUTION_CHART_SIZE = 10

# Comparaison des sources : période observée et score d'une offre intéressante
SOURCE_COMPARISON_DAYS = 30
GOOD_MATCH_SCORE = 50

# Offres « à saisir vite » : publiées depuis peu, bien notées et pas encore
# traitées. Les premières candidatures sont souvent les mieux lues.
HOT_OFFER_HOURS = 48
HOT_OFFER_SCORE = 70
HOT_OFFERS_LIMIT = 5

# Offres marquées « Intéressé » sans candidature depuis ce délai : rappelées
WAITING_INTEREST_DAYS = 5

# Offres retenues (suivies au-delà d'un simple coup d'œil) et candidatures envoyées
KEPT_STATUSES = ("INTERESTED", "APPLIED", "INTERVIEW", "REJECTED", "ACCEPTED")
SENT_STATUSES = ("APPLIED", "INTERVIEW", "REJECTED", "ACCEPTED")


def load_statistics(pDatabaseFile, pNow=None):
    """Calcule les indicateurs, les dernières exécutions et l'activité par jour."""

    vNow = pNow if pNow is not None else datetime.now()
    vNewOfferDays = load_settings(pDatabaseFile)["new_offer_days"]
    vActivity = {
        vName: vCount(pDatabaseFile, max(CHART_DAYS, 2 * WEEK_DAYS), vNow)
        for vName, (_, vCount) in WEEK_SERIES.items()
    }

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
        "withdrawn_offers": list_withdrawn_offers(pDatabaseFile),
        "hot_offers": find_hot_offers(pDatabaseFile, vNow),
        "waiting_interests": get_waiting_interests(
            pDatabaseFile, vNow - timedelta(days=WAITING_INTEREST_DAYS)
        )[:DASHBOARD_LIST_SIZE],
        "preferred_offers": find_preferred_offers(
            pDatabaseFile, vNow - timedelta(days=vNewOfferDays)
        ),
        "executions": get_history(pDatabaseFile, pLimit=RECENT_EXECUTIONS),
        "daily_activity": trim_leading_empty_days(
            {vName: vActivity[vName][-CHART_DAYS:] for vName in ACTIVITY_SERIES}
        ),
        "week_summary": summarize_week(vActivity),
    }

    return rStatistics


def summarize_week(pActivity, pDays=WEEK_DAYS):
    """Compare, série par série, les pDays derniers jours aux pDays précédents."""

    rWeek = []

    for vName, vCounts in pActivity.items():
        vValues = [vCount for _, vCount in vCounts]
        vCurrent = sum(vValues[-pDays:])
        vPrevious = sum(vValues[-2 * pDays : -pDays])

        rWeek.append(
            {
                "name": vName,
                "label": WEEK_SERIES[vName][0],
                "current": vCurrent,
                "previous": vPrevious,
                "trend": describe_trend(vCurrent - vPrevious),
            }
        )

    return rWeek


def build_month_summary(pDatabaseFile, pNow):
    """Retourne le bilan des 30 derniers jours comparés aux 30 précédents, et les
    entretiens obtenus par source sur le mois.
    """

    vActivity = {
        vName: vCount(pDatabaseFile, 2 * MONTH_DAYS, pNow)
        for vName, (_, vCount) in WEEK_SERIES.items()
    }

    rMonth = {
        "rows": summarize_week(vActivity, MONTH_DAYS),
        "interview_sources": [
            (get_source_label(vSource), vCount)
            for vSource, vCount in count_interviews_by_source(
                pDatabaseFile, pNow - timedelta(days=MONTH_DAYS)
            )
        ],
    }

    return rMonth


def describe_interview_sources(pSources):
    """Résume les entretiens du mois par source, ou indique qu'il n'y en a pas."""

    rText = (
        "Entretiens obtenus ce mois-ci : "
        + ", ".join(f"{vLabel} {vCount}" for vLabel, vCount in pSources)
        if pSources
        else "Aucun entretien obtenu ces 30 derniers jours."
    )

    return rText


def describe_trend(pDelta):
    """Décrit un écart d'une semaine à l'autre : « +3 », « −2 » ou « = »."""

    if pDelta > 0:
        rTrend = f"+{pDelta}"
    elif pDelta < 0:
        rTrend = f"\u2212{-pDelta}"
    else:
        rTrend = "="

    return rTrend


def find_hot_offers(pDatabaseFile, pNow, pLimit=HOT_OFFERS_LIMIT):
    """Retourne les offres à saisir vite : vues et publiées depuis HOT_OFFER_HOURS,
    sans statut, avec une correspondance d'au moins HOT_OFFER_SCORE %.
    """

    vSince = pNow - timedelta(hours=HOT_OFFER_HOURS)
    vOffers = [
        vOffer
        for vOffer in map(
            clean_missing_values,
            get_offers(pDatabaseFile, pSeenSince=vSince, pHideIgnored=True).to_dict(
                "records"
            ),
        )
        if not vOffer.get("application_status")
        and str(vOffer.get("published_at") or vSince.isoformat())[:10]
        >= vSince.date().isoformat()
    ]

    score_offers(vOffers, load_profile(pDatabaseFile))

    rOffers = sorted(
        (
            vOffer
            for vOffer in vOffers
            if (vOffer.get("match_score") or 0) >= HOT_OFFER_SCORE
        ),
        key=lambda pOffer: -pOffer["match_score"],
    )[:pLimit]

    return rOffers


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


def load_scored_offers(pDatabaseFile, pNow, pDays=SOURCE_COMPARISON_DAYS):
    """Retourne les offres de la période, notées une fois pour les deux comparaisons."""

    rOffers = get_offers(
        pDatabaseFile, pSeenSince=pNow - timedelta(days=pDays)
    ).to_dict("records")
    score_offers(rOffers, load_profile(pDatabaseFile))

    return rOffers


def compare_sources(pDatabaseFile, pNow, pDays=SOURCE_COMPARISON_DAYS, pOffers=None):
    """Retourne, par source, les offres découvertes sur la période et leur intérêt.

    Une source utile apporte des offres proches du profil, retenues ou menant à
    une candidature, pas seulement beaucoup d'offres. Tri : les plus utiles en tête.
    """

    vOffers = (
        pOffers
        if pOffers is not None
        else load_scored_offers(pDatabaseFile, pNow, pDays)
    )

    vGroups = {}

    for vOffer in vOffers:
        vGroups.setdefault(vOffer["source"], []).append(vOffer)

    rComparison = sort_comparison(
        [
            {
                "source": vSource,
                **summarize_offers(get_source_label(vSource), vGroup),
            }
            for vSource, vGroup in vGroups.items()
        ]
    )

    return rComparison


def summarize_offers(pLabel, pOffers):
    """Résume un groupe d'offres notées : nombre, bon score, suites données."""

    vScores = [
        vOffer["match_score"] for vOffer in pOffers if vOffer["match_score"] is not None
    ]
    vStatuses = [vOffer.get("application_status") for vOffer in pOffers]
    vGood = sum(vScore >= GOOD_MATCH_SCORE for vScore in vScores)

    rRow = {
        "label": pLabel,
        "offers": len(pOffers),
        "good": vGood,
        "kept": sum(vStatus in KEPT_STATUSES for vStatus in vStatuses),
        "sent": sum(vStatus in SENT_STATUSES for vStatus in vStatuses),
        "ignored": sum(vStatus == "IGNORED" for vStatus in vStatuses),
        "good_rate": round(100 * vGood / len(pOffers)) if pOffers else 0,
        "average_score": round(sum(vScores) / len(vScores)) if vScores else None,
    }

    return rRow


def sort_comparison(pRows):
    """Trie les lignes : celles qui mènent le plus à des candidatures en tête."""

    rRows = sorted(
        pRows,
        key=lambda pRow: (
            -pRow["sent"],
            -pRow["kept"],
            -pRow["good"],
            -pRow["offers"],
            pRow["label"],
        ),
    )

    return rRows


def compare_saved_searches(
    pDatabaseFile, pNow, pDays=SOURCE_COMPARISON_DAYS, pOffers=None
):
    """Retourne, par recherche enregistrée, les offres de la période qui répondent
    à ses critères et les suites données, comme pour les sources.

    L'offre ne garde pas la recherche qui l'a trouvée : ses critères (mot-clé,
    synonymes compris, et lieu) sont appliqués aux offres en base.
    """

    vOffers = (
        pOffers
        if pOffers is not None
        else load_scored_offers(pDatabaseFile, pNow, pDays)
    )

    vRows = []

    for vSearch in get_saved_searches(pDatabaseFile):
        vKeyword = vSearch["criteria"].get("keyword")
        vLocation = vSearch["criteria"].get("location")
        vMatching = [
            vOffer
            for vOffer in vOffers
            if (not vKeyword or matches_keyword(vOffer, vKeyword))
            and (not vLocation or matches_location(vOffer, vLocation))
        ]

        if vMatching:
            vRows.append(summarize_offers(vSearch["name"], vMatching))

    rComparison = sort_comparison(vRows)

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

# Dernière revue quotidienne de l'utilité des sources (run_due_source_review)
SOURCE_REVIEW_KEY = "source_review"


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


def run_due_source_review(pDatabaseFile, pNow):
    """Revoit chaque jour l'utilité des sources et garde le conseil en base.

    La comparaison note toutes les offres du mois : trop longue pour une page,
    elle est faite par le planificateur et lue ensuite par la page Santé.
    """

    vToday = pNow.date().isoformat()

    if load_source_review(pDatabaseFile).get("date") == vToday:
        return None

    rReview = {
        "date": vToday,
        "advice": describe_useless_sources(compare_sources(pDatabaseFile, pNow)),
    }
    save_json_setting(pDatabaseFile, SOURCE_REVIEW_KEY, rReview)

    logger.info(
        "Utilité des sources revue : %s", rReview["advice"] or "rien à signaler"
    )

    return rReview


def load_source_review(pDatabaseFile):
    """Retourne la dernière revue des sources, vide si elle n'a jamais eu lieu."""

    rReview = load_json_setting(pDatabaseFile, SOURCE_REVIEW_KEY, {}, dict)

    return rReview
