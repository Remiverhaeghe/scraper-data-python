"""Récapitulatif quotidien facultatif : offres du jour, relances dues, entretiens du lendemain

Envoyé une fois par jour, à partir de l'heure réglée dans les Paramètres
(0 : désactivé), à l'adresse des notifications.
"""

from datetime import timedelta
from html import escape

from config import APPLICATION_NAME
from job.application_tracking import get_due_follow_ups
from job.notification import describe_follow_up, describe_offer
from job.settings import load_settings
from job.weekly_digest import (
    build_section,
    describe_interview,
    get_coming_interviews,
    get_new_offers,
)
from storage.settings_repository import get_setting_values, save_setting_values
from utils.logger import get_logger

logger = get_logger(__name__)

DAILY_DIGEST_KEY = "daily_digest_sent"


def build_daily_digest(pDatabaseFile, pNow):
    """Rassemble les offres des dernières 24 heures, les relances dues et les
    entretiens du lendemain.
    """

    vSince = (pNow - timedelta(days=1)).isoformat()
    vTomorrow = (pNow + timedelta(days=1)).isoformat(timespec="minutes")

    rDigest = {
        "offers": [
            vOffer
            for vOffer in get_new_offers(pDatabaseFile, pNow)
            if str(vOffer.get("first_seen_at") or "") >= vSince
        ],
        "follow_ups": get_due_follow_ups(pDatabaseFile, pNow),
        "interviews": [
            vInterview
            for vInterview in get_coming_interviews(pDatabaseFile, pNow)
            if vInterview["interview_at"] <= vTomorrow
        ],
    }

    return rDigest


def build_daily_email(pDigest):
    """Construit le sujet, le texte et le HTML du récapitulatif du jour."""

    vSections = [
        build_section(
            "Nouvelles offres du jour",
            pDigest["offers"],
            describe_offer,
            "Aucune nouvelle offre depuis hier.",
        ),
        build_section(
            "Relances à faire",
            pDigest["follow_ups"],
            describe_follow_up,
            "Aucune relance due aujourd'hui.",
        ),
        build_section(
            "Entretiens de demain",
            pDigest["interviews"],
            describe_interview,
            "Aucun entretien demain.",
        ),
    ]

    vSubject = (
        f"{APPLICATION_NAME} : votre journée, {len(pDigest['offers'])} offre(s), "
        f"{len(pDigest['follow_ups'])} relance(s), "
        f"{len(pDigest['interviews'])} entretien(s)"
    )

    rEmail = (
        vSubject,
        "\n".join(vText for vText, _ in vSections),
        "".join(vHtml for _, vHtml in vSections) or escape(vSubject),
    )

    return rEmail


def is_daily_digest_due(pDatabaseFile, pNow):
    """Indique si le récapitulatif du jour doit partir : heure atteinte, pas encore
    envoyé aujourd'hui.
    """

    vHour = load_settings(pDatabaseFile)["daily_digest_hour"]
    vSent = get_setting_values(pDatabaseFile).get(DAILY_DIGEST_KEY)

    rDue = bool(vHour) and pNow.hour >= vHour and vSent != pNow.date().isoformat()

    return rDue


def mark_daily_digest_sent(pDatabaseFile, pNow):
    """Note l'envoi du jour : le récapitulatif ne repart pas avant demain."""

    save_setting_values(pDatabaseFile, {DAILY_DIGEST_KEY: pNow.date().isoformat()})

    logger.info("Récapitulatif quotidien envoyé")


def send_daily_digest_if_due(pDatabaseFile, pNow, pEmail, pSend):
    """Envoie le récapitulatif du jour s'il est dû ; retourne s'il est parti."""

    if not pEmail or not is_daily_digest_due(pDatabaseFile, pNow):
        return False

    pSend(pEmail, *build_daily_email(build_daily_digest(pDatabaseFile, pNow)))
    mark_daily_digest_sent(pDatabaseFile, pNow)

    return True
