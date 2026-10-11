"""Suivi des candidatures par colonnes et statistiques de réponse"""

import re

from job.fingerprint import normalize
from job.presentation import (
    STATUS_LABELS,
    format_date,
    get_source_label,
)
from storage.job_applications import (
    SENT_STATUSES,
    get_applications_with_offers,
)
from storage.job_offers import FOLLOW_UP_STATUSES

# Colonnes du tableau de suivi et statuts qu'elles regroupent
BOARD_COLUMNS = (
    ("to_apply", "À postuler", ("INTERESTED",)),
    ("applied", "Postulé", ("APPLIED",)),
    ("interview", "Entretien", ("INTERVIEW",)),
    ("answer", "Réponse", ("ACCEPTED", "REJECTED")),
)

# Statuts proposés sur une carte ; « Clôturé » la retire du tableau.
BOARD_STATUSES = (
    "INTERESTED",
    "APPLIED",
    "INTERVIEW",
    "ACCEPTED",
    "REJECTED",
    "CLOSED",
)

# Une candidature a reçu une réponse dès qu'elle a quitté le statut « Postulé ».
ANSWERED_STATUSES = ("INTERVIEW", "ACCEPTED", "REJECTED")

# Familles de poste reconnues dans le titre normalisé, la première trouvée l'emporte :
# « Data engineer » est rangé en Data plutôt qu'en Développement.
JOB_FAMILIES = (
    (
        "Data et IA",
        r"\b(data|donnees|machine learning|ml|ia|ai|bi|analyst|analyste|scientist)\b",
    ),
    (
        "DevOps et cloud",
        r"\b(devops|sre|cloud|infra|infrastructure|kubernetes|systemes?|reseaux?)\b",
    ),
    ("Test et qualité", r"\b(test|testeur|tester|qa|qualite|recette)\b"),
    (
        "Projet et produit",
        r"\b(chef de projet|project|product|produit|scrum|po|pm)\b",
    ),
    (
        "Développement",
        r"\b(developpeur|developer|dev|engineer|ingenieur|programmeur|software"
        r"|logiciel|full ?stack|backend|frontend)\b",
    ),
)
OTHER_FAMILY = "Autre"

# Lignes affichées par tableau de statistiques, les plus fournies d'abord
MAX_STATISTIC_ROWS = 10


def get_job_family(pTitle):
    """Range un titre d'offre dans une famille de poste."""

    vTitle = normalize(pTitle)

    rFamily = next(
        (vFamily for vFamily, vPattern in JOB_FAMILIES if re.search(vPattern, vTitle)),
        OTHER_FAMILY,
    )

    return rFamily


def prepare_card(pApplication, pNow):
    """Complète une candidature avec les informations affichées sur sa carte."""

    rCard = dict(pApplication)

    rCard["status_label"] = STATUS_LABELS.get(rCard["status"], rCard["status"])
    rCard["source_label"] = get_source_label(rCard["source"])
    rCard["applied_label"] = format_date(rCard["applied_at"])
    rCard["follow_up_label"] = format_date(rCard["follow_up_date"])
    rCard["follow_up_due"] = bool(
        rCard["status"] in FOLLOW_UP_STATUSES
        and rCard["follow_up_date"]
        and rCard["follow_up_date"] <= pNow.isoformat()
    )

    return rCard


def build_board(pDatabaseFile, pNow):
    """Retourne les colonnes du tableau de suivi et leurs cartes."""

    vStatuses = [vStatus for _, _, vGroup in BOARD_COLUMNS for vStatus in vGroup]
    vCards = [
        prepare_card(vApplication, pNow)
        for vApplication in get_applications_with_offers(pDatabaseFile, vStatuses)
    ]

    rBoard = [
        {
            "key": vKey,
            "label": vLabel,
            "cards": [vCard for vCard in vCards if vCard["status"] in vGroup],
        }
        for vKey, vLabel, vGroup in BOARD_COLUMNS
    ]

    return rBoard


def count_by(pApplications, pGetLabel):
    """Compte envois et réponses par libellé ; retourne les lignes les plus fournies."""

    vCounts = {}

    for vApplication in pApplications:
        vLabel = pGetLabel(vApplication)
        vSent, vAnswered = vCounts.get(vLabel, (0, 0))

        vCounts[vLabel] = (
            vSent + 1,
            vAnswered + (vApplication["status"] in ANSWERED_STATUSES),
        )

    vRows = [
        {
            "label": vLabel,
            "sent": vSent,
            "answered": vAnswered,
            "rate": round(100 * vAnswered / vSent),
        }
        for vLabel, (vSent, vAnswered) in sorted(
            vCounts.items(), key=lambda pItem: (-pItem[1][0], pItem[0])
        )
    ]

    rRows = vRows[:MAX_STATISTIC_ROWS]

    return rRows


def build_application_statistics(pDatabaseFile):
    """Calcule le taux de réponse global, par source, par famille de poste et par société."""

    vApplications = get_applications_with_offers(pDatabaseFile, SENT_STATUSES)

    vAnswered = sum(
        vApplication["status"] in ANSWERED_STATUSES for vApplication in vApplications
    )

    rStatistics = {
        "sent": len(vApplications),
        "answered": vAnswered,
        "interviews": sum(
            vApplication["status"] in ("INTERVIEW", "ACCEPTED")
            for vApplication in vApplications
        ),
        "rate": round(100 * vAnswered / len(vApplications)) if vApplications else None,
        "tables": [
            (
                "Par source",
                count_by(
                    vApplications,
                    lambda pApplication: get_source_label(pApplication["source"]),
                ),
            ),
            (
                "Par type de poste",
                count_by(
                    vApplications,
                    lambda pApplication: get_job_family(pApplication["title"]),
                ),
            ),
            (
                "Par société",
                count_by(
                    vApplications,
                    lambda pApplication: pApplication["company"] or "Non communiquée",
                ),
            ),
        ],
    }

    return rStatistics


def get_due_follow_ups(pDatabaseFile, pNow):
    """Retourne les candidatures dont la relance est due, la plus ancienne en tête."""

    vCards = [
        prepare_card(vApplication, pNow)
        for vApplication in get_applications_with_offers(
            pDatabaseFile, FOLLOW_UP_STATUSES
        )
    ]

    rFollowUps = sorted(
        (vCard for vCard in vCards if vCard["follow_up_due"]),
        key=lambda pCard: pCard["follow_up_date"],
    )

    return rFollowUps
