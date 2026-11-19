"""Bilan mensuel de la recherche, envoyé par e-mail au début du mois suivant

Le bilan reprend les démarches du mois (job/search_journal.py), les compare au
mois précédent et ajoute le délai moyen de réponse des recruteurs. Il part au
premier passage du planificateur du mois, pour le mois écoulé, à l'adresse des
notifications ; sans adresse, il reste lisible dans le récapitulatif du mois.
"""

from datetime import date, timedelta
from html import escape

from config import APPLICATION_NAME
from job.application_tracking import format_delay, get_average_delay
from job.search_journal import JOURNAL_STATUSES, MONTH_NAMES, build_monthly_report
from storage.job_applications import get_applications_with_offers
from storage.settings_repository import get_setting_values, save_setting_values
from utils.logger import get_logger

logger = get_logger(__name__)

# Mois AAAA-MM du dernier bilan envoyé : un seul par mois
REVIEW_KEY = "monthly_review_sent"

# Lignes du bilan : démarche du journal et libellé dans l'e-mail
REVIEW_LINES = (
    ("Candidature envoyée", "Candidatures"),
    ("Candidature spontanée", "Candidatures spontanées"),
    ("Relance", "Relances"),
    ("Réponse reçue", "Réponses reçues"),
    ("Entretien", "Entretiens"),
)


def get_previous_month(pMonth):
    """Retourne le premier jour du mois qui précède."""

    rMonth = (pMonth - timedelta(days=1)).replace(day=1)

    return rMonth


def is_in_month(pValue, pMonth):
    """Indique si une date ISO enregistrée tombe dans le mois donné."""

    rInMonth = bool(pValue) and str(pValue)[:7] == f"{pMonth:%Y-%m}"

    return rInMonth


def compute_average_delay(pDatabaseFile, pMonth):
    """Retourne le délai moyen, en jours, des réponses reçues dans le mois."""

    vAnswered = [
        vApplication
        for vApplication in get_applications_with_offers(
            pDatabaseFile, JOURNAL_STATUSES
        )
        if is_in_month(vApplication.get("responded_at"), pMonth)
    ]

    rDelay = get_average_delay(vAnswered)

    return rDelay


def build_monthly_review(pDatabaseFile, pMonth):
    """Retourne le bilan d'un mois : nombres comparés au mois précédent et délai."""

    vCounts = dict(build_monthly_report(pDatabaseFile, pMonth)["counts"])
    vPrevious = dict(
        build_monthly_report(pDatabaseFile, get_previous_month(pMonth))["counts"]
    )
    vMonthName = MONTH_NAMES[pMonth.month - 1]
    # « d'octobre », « de mai », comme le récapitulatif du mois
    vOf = "d'" if vMonthName[0] in "aeiouéè" else "de "

    rReview = {
        "month": f"{pMonth:%Y-%m}",
        "title": f"Bilan {vOf}{vMonthName} {pMonth.year}",
        "lines": [
            {
                "label": vLabel,
                "count": vCounts.get(vStep, 0),
                "previous": vPrevious.get(vStep, 0),
            }
            for vStep, vLabel in REVIEW_LINES
        ],
        "average_delay": compute_average_delay(pDatabaseFile, pMonth),
    }

    return rReview


def describe_change(pCurrent, pPrevious):
    """Décrit l'écart avec le mois précédent : « +2 », « −1 » ou « = »."""

    vDelta = pCurrent - pPrevious

    if vDelta > 0:
        rText = f"+{vDelta}"
    elif vDelta < 0:
        rText = f"−{-vDelta}"
    else:
        rText = "="

    return rText


def build_review_email(pReview):
    """Construit le sujet, le texte et le HTML du bilan mensuel."""

    vLines = [
        f"{vLine['label']} : {vLine['count']} "
        f"({describe_change(vLine['count'], vLine['previous'])} sur le mois précédent)"
        for vLine in pReview["lines"]
    ]
    vDelay = (
        "Délai moyen de réponse : "
        + (
            "aucune réponse reçue ce mois-ci"
            if pReview["average_delay"] is None
            else format_delay(pReview["average_delay"])
        )
        + "."
    )
    vNote = (
        "Le détail daté des démarches est dans Candidatures > Journal de "
        "recherche, récapitulatif du mois."
    )

    vSubject = f"{APPLICATION_NAME} : {pReview['title'].lower()}"
    vText = "\n".join([pReview["title"], "", *vLines, vDelay, "", vNote])
    vHtml = (
        f"<h2>{escape(pReview['title'])}</h2><ul>"
        + "".join(f"<li>{escape(vLine)}</li>" for vLine in vLines)
        + f"</ul><p>{escape(vDelay)}</p><p>{escape(vNote)}</p>"
    )

    rEmail = (vSubject, vText, vHtml)

    return rEmail


def get_due_month(pDatabaseFile, pNow):
    """Retourne le mois écoulé dont le bilan reste à envoyer, ou None."""

    vMonth = get_previous_month(date(pNow.year, pNow.month, 1))

    rMonth = (
        None
        if get_setting_values(pDatabaseFile).get(REVIEW_KEY) == f"{vMonth:%Y-%m}"
        else vMonth
    )

    return rMonth


def send_monthly_review_if_due(pDatabaseFile, pNow, pEmail, pSend):
    """Envoie le bilan du mois écoulé s'il n'est pas encore parti ; retourne True
    s'il est parti.

    pSend est la fonction d'envoi (utils.mailer.send_email), remplacée en test.
    """

    vMonth = get_due_month(pDatabaseFile, pNow) if pEmail else None

    if vMonth is None:
        return False

    pSend(pEmail, *build_review_email(build_monthly_review(pDatabaseFile, vMonth)))
    save_setting_values(pDatabaseFile, {REVIEW_KEY: f"{vMonth:%Y-%m}"})

    logger.info("Bilan mensuel envoyé pour %s", f"{vMonth:%Y-%m}")

    return True
