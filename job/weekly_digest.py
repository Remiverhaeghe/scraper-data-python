"""Récapitulatif hebdomadaire par e-mail : offres, relances, entretiens et préparation"""

from datetime import timedelta
from html import escape

from config import APPLICATION_NAME
from job.application_tracking import get_week_follow_ups
from job.notification import describe_follow_up, describe_offer
from job.preparation import score_offers
from job.presentation import clean_missing_values, format_date, safe_url
from job.profile import load_profile
from job.quiz import load_active_quiz
from job.skills_dashboard import build_skills_dashboard
from storage.job_applications import get_applications_with_offers
from storage.job_offers import get_offers
from storage.settings_repository import get_setting_values, save_setting_values
from utils.logger import get_logger

logger = get_logger(__name__)

# Semaine ISO du dernier récapitulatif envoyé : un seul par semaine
DIGEST_KEY = "weekly_digest_sent"

# Offres les mieux notées reprises dans le récapitulatif
MAX_DIGEST_OFFERS = 10

DIGEST_DAYS = 7


def get_week_key(pNow):
    """Retourne la semaine ISO d'une date, par exemple 2026-W43."""

    vYear, vWeek, _ = pNow.isocalendar()

    rKey = f"{vYear}-W{vWeek:02d}"

    return rKey


def get_new_offers(pDatabaseFile, pNow):
    """Retourne les offres vues dans la semaine, les mieux notées en tête."""

    vOffers = [
        clean_missing_values(vOffer)
        for vOffer in get_offers(
            pDatabaseFile,
            pSeenSince=pNow - timedelta(days=DIGEST_DAYS),
            pHideIgnored=True,
        ).to_dict("records")
    ]

    score_offers(vOffers, load_profile(pDatabaseFile))

    rOffers = sorted(
        vOffers,
        key=lambda pOffer: (
            -1 if pOffer["match_score"] is None else pOffer["match_score"]
        ),
        reverse=True,
    )[:MAX_DIGEST_OFFERS]

    return rOffers


def get_coming_interviews(pDatabaseFile, pNow):
    """Retourne les entretiens prévus dans les sept prochains jours."""

    vStart = pNow.isoformat(timespec="minutes")
    vEnd = (pNow + timedelta(days=DIGEST_DAYS)).isoformat(timespec="minutes")

    rInterviews = sorted(
        (
            vApplication
            for vApplication in get_applications_with_offers(
                pDatabaseFile, ("INTERVIEW",)
            )
            if vApplication.get("interview_at")
            and vStart <= vApplication["interview_at"] <= vEnd
        ),
        key=lambda pApplication: pApplication["interview_at"],
    )

    return rInterviews


def build_weekly_digest(pDatabaseFile, pNow):
    """Rassemble le contenu du récapitulatif de la semaine."""

    vDashboard = build_skills_dashboard(
        pDatabaseFile, load_active_quiz(pDatabaseFile), pNow.date()
    )

    rDigest = {
        "offers": get_new_offers(pDatabaseFile, pNow),
        "follow_ups": get_week_follow_ups(pDatabaseFile, pNow),
        "interviews": get_coming_interviews(pDatabaseFile, pNow),
        "readiness": vDashboard["summary"]["readiness"],
        "priority": vDashboard["summary"]["priority"],
    }

    return rDigest


def describe_interview(pApplication):
    """Résume un entretien : date et entreprise."""

    rText = " · ".join(
        vPart
        for vPart in (
            f"le {format_date(pApplication['interview_at'])}",
            pApplication.get("company"),
        )
        if vPart
    )

    return rText


def build_section(pTitle, pItems, pDescribe, pEmptyText):
    """Construit une section de l'e-mail en texte et en HTML."""

    vTextLines = [pTitle, ""]
    vHtml = f"<h2>{escape(pTitle)}</h2>"

    if not pItems:
        vTextLines += [pEmptyText, ""]
        vHtml += f"<p>{escape(pEmptyText)}</p>"

    else:
        vHtmlItems = []

        for vItem in pItems:
            vTitle = vItem.get("title") or "Titre non communiqué"
            vDetail = pDescribe(vItem)
            vUrl = safe_url(vItem.get("url"))

            vTextLines += [vTitle, vDetail, vUrl, ""]
            # Tout texte venant d'une offre est échappé : l'e-mail est lu en HTML.
            vHtmlItems.append(
                f'<li><a href="{escape(vUrl)}">{escape(vTitle)}</a>'
                f"<br><small>{escape(vDetail)}</small></li>"
            )

        vHtml += f"<ul>{''.join(vHtmlItems)}</ul>"

    rSection = ("\n".join(vTextLines), vHtml)

    return rSection


def build_digest_email(pDigest):
    """Construit le sujet, le texte et le HTML du récapitulatif."""

    vSections = [
        build_section(
            "Offres de la semaine les mieux notées",
            pDigest["offers"],
            describe_offer,
            "Aucune nouvelle offre cette semaine.",
        ),
        build_section(
            "Relances à faire",
            pDigest["follow_ups"],
            describe_follow_up,
            "Aucune relance prévue dans les sept prochains jours.",
        ),
        build_section(
            "Entretiens à venir",
            pDigest["interviews"],
            describe_interview,
            "Aucun entretien prévu dans les sept prochains jours.",
        ),
    ]

    vPreparation = (
        f"Préparation des compétences demandées : {pDigest['readiness']} %"
        + (f", priorité : {pDigest['priority']}." if pDigest["priority"] else ".")
    )

    vSubject = (
        f"{APPLICATION_NAME} : votre semaine, {len(pDigest['offers'])} offre(s), "
        f"{len(pDigest['follow_ups'])} relance(s), "
        f"{len(pDigest['interviews'])} entretien(s)"
    )
    vText = "\n".join([*(vText for vText, _ in vSections), vPreparation])
    vHtml = "".join(vHtml for _, vHtml in vSections) + f"<p>{escape(vPreparation)}</p>"

    rEmail = (vSubject, vText, vHtml)

    return rEmail


def is_digest_due(pDatabaseFile, pNow):
    """Indique si le récapitulatif de la semaine reste à envoyer.

    Il part au premier passage du planificateur de la semaine, le lundi en général.
    """

    rDue = get_setting_values(pDatabaseFile).get(DIGEST_KEY) != get_week_key(pNow)

    return rDue


def mark_digest_sent(pDatabaseFile, pNow):
    """Note la semaine du récapitulatif envoyé."""

    save_setting_values(pDatabaseFile, {DIGEST_KEY: get_week_key(pNow)})

    logger.info("Récapitulatif hebdomadaire envoyé pour %s", get_week_key(pNow))
