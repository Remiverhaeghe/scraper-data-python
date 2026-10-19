"""Rappel la veille d'un entretien : offre, questions probables, STAR et révision"""

from datetime import timedelta
from html import escape

from config import APPLICATION_NAME
from job.interview_journal import collect_asked_questions
from job.interview_revision import build_offer_revision
from job.preparation import prepare_application
from job.presentation import format_date, safe_url
from job.profile import load_profile
from job.quiz import load_active_quiz
from job.star_answers import load_star_answers
from storage.job_applications import get_applications_with_offers
from storage.job_offers import get_offer
from storage.settings_repository import load_json_setting, save_json_setting
from utils.logger import get_logger

logger = get_logger(__name__)

# Entretiens déjà rappelés : une clé par offre et par date d'entretien
REMINDERS_KEY = "interview_reminders_sent"

# Délai avant l'entretien dans lequel le rappel part
REMINDER_DELAY = timedelta(hours=24)

# Thèmes de révision repris dans le rappel, les moins maîtrisés d'abord
MAX_REMINDER_THEMES = 5


def get_reminder_key(pApplication):
    """Retourne la clé d'un entretien : un report de date donne un nouveau rappel."""

    rKey = (
        f"{pApplication['source']}|{pApplication['source_id']}|"
        f"{pApplication['interview_at']}"
    )

    return rKey


def get_interviews_to_remind(pDatabaseFile, pNow):
    """Retourne les entretiens des prochaines 24 heures pas encore rappelés."""

    vSent = set(load_json_setting(pDatabaseFile, REMINDERS_KEY, [], list))
    vStart = pNow.isoformat(timespec="minutes")
    vEnd = (pNow + REMINDER_DELAY).isoformat(timespec="minutes")

    rInterviews = [
        vApplication
        for vApplication in get_applications_with_offers(pDatabaseFile, ("INTERVIEW",))
        if vApplication.get("interview_at")
        and vStart <= vApplication["interview_at"] <= vEnd
        and get_reminder_key(vApplication) not in vSent
    ]

    return rInterviews


def mark_reminded(pDatabaseFile, pApplication):
    """Note qu'un entretien a été rappelé."""

    vSent = load_json_setting(pDatabaseFile, REMINDERS_KEY, [], list)
    vSent.append(get_reminder_key(pApplication))

    save_json_setting(pDatabaseFile, REMINDERS_KEY, vSent)


def get_revision_themes(pDatabaseFile, pOffer):
    """Retourne les thèmes à revoir pour l'offre ; vide si la révision est illisible."""

    try:
        vThemes = build_offer_revision(
            pDatabaseFile, load_active_quiz(pDatabaseFile), pOffer
        )["themes"]

    except Exception:
        logger.exception("Révision illisible pour le rappel d'entretien")

        vThemes = []

    rThemes = [
        f"{vTheme['label']} : {vTheme['score']} % acquis"
        for vTheme in vThemes[:MAX_REMINDER_THEMES]
    ]

    return rThemes


def build_reminder_email(pDatabaseFile, pApplication):
    """Construit le sujet, le texte et le HTML du rappel d'un entretien."""

    vOffer = get_offer(pDatabaseFile, pApplication["source"], pApplication["source_id"])
    vInterview = prepare_application(
        load_profile(pDatabaseFile),
        vOffer,
        load_star_answers(pDatabaseFile),
        collect_asked_questions(pDatabaseFile),
    )["interview"]

    vTitle = vOffer.get("title") or "offre sans titre"
    vSections = [
        (
            "Questions comportementales probables",
            [
                f"{vItem['question']} ({'réponse préparée' if vItem['prepared'] else 'à préparer'})"
                for vItem in vInterview["likely"]
            ],
        ),
        (
            "Vos réponses STAR",
            [f"{vItem['question']}\n{vItem['text']}" for vItem in vInterview["star"]],
        ),
        (
            "Questions déjà posées en entretien",
            [vItem["question"] for vItem in vInterview["asked"]],
        ),
        ("Thèmes à revoir", get_revision_themes(pDatabaseFile, vOffer)),
        ("Questions à poser", vInterview["questions"]),
    ]

    vIntroduction = (
        f"Entretien le {format_date(pApplication['interview_at'])} pour le poste de "
        f"{vTitle}" + (f" chez {vOffer['company']}" if vOffer.get("company") else "")
    )
    vUrl = safe_url(vOffer.get("url"))

    vTextLines = [vIntroduction, vUrl, ""]
    vHtml = f'<p><a href="{escape(vUrl)}">{escape(vIntroduction)}</a></p>'

    for vHeading, vItems in vSections:
        if vItems:
            vTextLines += [vHeading, *(f"- {vItem}" for vItem in vItems), ""]
            # Tout texte venant d'une offre ou d'une saisie est échappé.
            vHtml += (
                f"<h2>{escape(vHeading)}</h2><ul>"
                + "".join(
                    f"<li>{escape(vItem).replace(chr(10), '<br>')}</li>"
                    for vItem in vItems
                )
                + "</ul>"
            )

    rEmail = (
        f"{APPLICATION_NAME} : entretien demain, {vTitle}",
        "\n".join(vTextLines),
        vHtml,
    )

    return rEmail
