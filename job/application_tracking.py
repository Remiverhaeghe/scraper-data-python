"""Suivi des candidatures par colonnes et statistiques de réponse"""

import re
from datetime import datetime, timedelta

from job.fingerprint import normalize
from job.preparation import score_offers
from job.presentation import (
    STATUS_LABELS,
    format_date,
    get_source_label,
)
from job.profile import load_profile
from job.settings import load_settings
from storage.job_applications import (
    ANSWERED_STATUSES,
    SENT_STATUSES,
    get_applications_with_offers,
    record_follow_up,
)
from storage.job_offers import FOLLOW_UP_STATUSES
from utils.logger import get_logger

logger = get_logger(__name__)

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

# Horizon de la vue des relances, en jours : la semaine à venir
FOLLOW_UP_HORIZON_DAYS = 7

# Niveaux de correspondance avec le profil, du plus exigeant au moins exigeant
MATCH_LEVELS = (
    (70, "Forte, 70 % et plus"),
    (40, "Moyenne, de 40 à 69 %"),
    (0, "Faible, moins de 40 %"),
)

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
    rCard["expired"] = rCard.get("availability") == "expired"
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


def get_response_days(pApplication):
    """Retourne le nombre de jours entre l'envoi et la première réponse, ou None."""

    vAppliedAt = pApplication.get("applied_at")
    vRespondedAt = pApplication.get("responded_at")

    rDays = None

    # La date de réponse n'est notée que depuis la version 19 de la base.
    if vAppliedAt and vRespondedAt:
        rDays = max(
            (
                datetime.fromisoformat(vRespondedAt)
                - datetime.fromisoformat(vAppliedAt)
            ).days,
            0,
        )

    return rDays


def get_average_delay(pApplications):
    """Retourne le délai de réponse moyen en jours, ou None s'il est inconnu."""

    vDays = [
        vDays for vDays in map(get_response_days, pApplications) if vDays is not None
    ]

    rDelay = round(sum(vDays) / len(vDays)) if vDays else None

    return rDelay


def format_delay(pDays):
    """Décrit un délai de réponse en jours, ou un tiret s'il est inconnu."""

    rText = "—" if pDays is None else f"{pDays} j"

    return rText


def get_match_level(pScore):
    """Retourne le libellé du niveau de correspondance d'un score."""

    # Score absent : l'offre ne cite aucune compétence reconnue.
    rLevel = (
        "Compétences non détectées"
        if pScore is None
        else next(vLabel for vMinimum, vLabel in MATCH_LEVELS if pScore >= vMinimum)
    )

    return rLevel


def count_by(pApplications, pGetLabel):
    """Compte envois, réponses et délai par libellé ; garde les lignes les plus fournies."""

    vGroups = {}

    for vApplication in pApplications:
        vGroups.setdefault(pGetLabel(vApplication), []).append(vApplication)

    vRows = []

    for vLabel, vGroup in sorted(
        vGroups.items(), key=lambda pItem: (-len(pItem[1]), pItem[0])
    ):
        vAnswered = sum(
            vApplication["status"] in ANSWERED_STATUSES for vApplication in vGroup
        )

        vRows.append(
            {
                "label": vLabel,
                "sent": len(vGroup),
                "answered": vAnswered,
                "rate": round(100 * vAnswered / len(vGroup)),
                "delay": format_delay(get_average_delay(vGroup)),
            }
        )

    rRows = vRows[:MAX_STATISTIC_ROWS]

    return rRows


def build_application_statistics(pDatabaseFile):
    """Calcule taux et délai de réponse, globalement puis par dimension."""

    vApplications = get_applications_with_offers(pDatabaseFile, SENT_STATUSES)

    score_offers(vApplications, load_profile(pDatabaseFile))

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
        "accepted": sum(
            vApplication["status"] == "ACCEPTED" for vApplication in vApplications
        ),
        "delay": format_delay(get_average_delay(vApplications)),
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
                "Par contrat",
                count_by(
                    vApplications,
                    lambda pApplication: pApplication["contract"] or "Non précisé",
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

    # Sans compétence dans le profil, aucun score n'est calculé.
    if any(vApplication["match_score"] is not None for vApplication in vApplications):
        rStatistics["tables"].insert(
            2,
            (
                "Par correspondance au profil",
                count_by(
                    vApplications,
                    lambda pApplication: get_match_level(pApplication["match_score"]),
                ),
            ),
        )

    rStatistics["funnel"] = build_funnel(rStatistics)

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


def build_follow_up_draft(pApplication, pName):
    """Rédige un message de relance à relire, à partir de la candidature."""

    vTitle = pApplication.get("title") or "proposé"
    vCompany = pApplication.get("company")
    vAppliedAt = pApplication.get("applied_at")

    vContext = f"ma candidature au poste de {vTitle}"

    if vCompany:
        vContext += f" chez {vCompany}"

    if vAppliedAt:
        vContext += f", envoyée le {format_date(vAppliedAt)}"

    if pApplication.get("status") == "INTERVIEW":
        vInterviewAt = pApplication.get("interview_at")
        vBody = (
            "Je vous remercie encore pour notre entretien"
            + (f" du {format_date(vInterviewAt)}" if vInterviewAt else "")
            + f" au sujet du poste de {vTitle}. Je me permets de revenir vers vous "
            "pour connaître la suite donnée à ma candidature.\n\n"
            "Notre échange a confirmé mon intérêt pour ce poste ; je reste "
            "disponible pour toute information complémentaire."
        )
    elif pApplication.get("follow_up_count"):
        vLastFollowUp = pApplication.get("last_follow_up_at")
        vBody = (
            f"Je reviens vers vous une dernière fois au sujet de {vContext}"
            + (
                f", restée sans réponse depuis ma relance du "
                f"{format_date(vLastFollowUp)}"
                if vLastFollowUp
                else ""
            )
            + ".\n\nSi le poste est pourvu, un mot de votre part me permettrait "
            "de clore ma candidature. Dans le cas contraire, ce poste m'intéresse "
            "toujours et je reste disponible pour un échange."
        )
    else:
        vBody = (
            f"Je me permets de revenir vers vous au sujet de {vContext}.\n\n"
            "Ce poste m'intéresse toujours et je reste disponible pour un échange "
            "à votre convenance."
        )

    rDraft = (
        f"Objet : ma candidature au poste de {vTitle}\n\n"
        "Bonjour,\n\n"
        f"{vBody}\n\n"
        f"Bien cordialement,\n{pName}"
    ).rstrip()

    return rDraft


def get_week_follow_ups(pDatabaseFile, pNow):
    """Retourne les relances en retard ou prévues dans la semaine, avec un brouillon."""

    vLimit = (pNow + timedelta(days=FOLLOW_UP_HORIZON_DAYS)).isoformat()
    vName = load_profile(pDatabaseFile)["name"]

    rFollowUps = []

    for vApplication in get_applications_with_offers(pDatabaseFile, FOLLOW_UP_STATUSES):
        vCard = prepare_card(vApplication, pNow)

        if vCard["follow_up_date"] and vCard["follow_up_date"] <= vLimit:
            vCard["draft"] = build_follow_up_draft(vCard, vName)
            rFollowUps.append(vCard)

    rFollowUps.sort(key=lambda pCard: pCard["follow_up_date"])

    return rFollowUps


def mark_followed_up(pDatabaseFile, pSource, pSourceId, pNow):
    """Note une relance faite et programme la suivante selon les paramètres."""

    record_follow_up(
        pDatabaseFile,
        pSource,
        pSourceId,
        pNow,
        load_settings(pDatabaseFile)["follow_up_days"],
    )

    logger.info("Relance notée : %s %s", pSource, pSourceId)


def build_funnel(pStatistics):
    """Retourne les étapes de l'entonnoir : nombre, part des envois et passage."""

    vStages = (
        ("Envoyées", pStatistics["sent"]),
        ("Réponses", pStatistics["answered"]),
        ("Entretiens", pStatistics["interviews"]),
        ("Acceptées", pStatistics["accepted"]),
    )

    rFunnel = []
    vPrevious = None

    for vLabel, vCount in vStages:
        rFunnel.append(
            {
                "label": vLabel,
                "count": vCount,
                "share": (
                    round(100 * vCount / pStatistics["sent"])
                    if pStatistics["sent"]
                    else 0
                ),
                # Passage depuis l'étape précédente ; la première n'en a pas.
                "conversion": round(100 * vCount / vPrevious) if vPrevious else None,
            }
        )
        vPrevious = vCount

    return rFunnel
