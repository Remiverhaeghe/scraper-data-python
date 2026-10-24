"""Vérification quotidienne des offres suivies : repère celles qui ont été retirées"""

import time
from datetime import timedelta

from config import APPLICATION_NAME
from job.notification import build_list_email
from job.presentation import STATUS_LABELS, format_date
from storage.job_applications import get_applications_with_offers
from storage.job_offers import set_availability
from storage.settings_repository import get_setting_values, save_setting_values
from utils.link_checker import check_offer_link
from utils.logger import get_logger

logger = get_logger(__name__)

# Offres dont la disparition change quelque chose : à postuler ou en cours
FOLLOWED_STATUSES = ("INTERESTED", "APPLIED", "INTERVIEW")

# Une offre n'est pas revérifiée avant ce délai
RECHECK_DELAY = timedelta(days=1)

# Requêtes vers les sites des offres : nombre limité par passage, par politesse
MAX_CHECKS_PER_RUN = 30

# Durée maximale d'un passage, en secondes : les sites lents ne retardent pas la
# recherche planifiée, les offres restantes sont vues au passage suivant.
MAX_CHECK_SECONDS = 120

# Jour de la dernière vérification : un seul passage par jour
LAST_CHECK_KEY = "followed_availability_checked"


def get_offers_to_check(pDatabaseFile, pNow):
    """Retourne les offres suivies encore disponibles et non vérifiées récemment."""

    vLimit = (pNow - RECHECK_DELAY).isoformat()

    rOffers = [
        vOffer
        for vOffer in get_applications_with_offers(pDatabaseFile, FOLLOWED_STATUSES)
        if vOffer.get("url")
        and vOffer.get("availability") != "expired"
        and (vOffer.get("availability_checked_at") or "") <= vLimit
    ][:MAX_CHECKS_PER_RUN]

    return rOffers


def check_followed_offers(
    pDatabaseFile, pNow, pCheck=check_offer_link, pClock=time.monotonic
):
    """Vérifie les liens des offres suivies ; retourne celles qui viennent d'être retirées."""

    rExpired = []
    vDeadline = pClock() + MAX_CHECK_SECONDS

    for vOffer in get_offers_to_check(pDatabaseFile, pNow):
        if pClock() > vDeadline:
            logger.warning(
                "Vérification des offres suivies arrêtée après %s s : la suite au "
                "prochain passage",
                MAX_CHECK_SECONDS,
            )
            break

        vAvailability = pCheck(vOffer["url"])

        # Sans réponse nette, rien n'est enregistré : l'offre sera revue demain.
        if vAvailability is None:
            continue

        set_availability(
            pDatabaseFile, vOffer["source"], vOffer["source_id"], vAvailability, pNow
        )

        if vAvailability == "expired":
            rExpired.append(vOffer)

    logger.info("Offres suivies vérifiées : %s retirée(s)", len(rExpired))

    return rExpired


def run_due_followed_check(pDatabaseFile, pNow, pCheck=check_offer_link):
    """Lance la vérification si elle n'a pas eu lieu aujourd'hui ; retourne les retirées."""

    vToday = pNow.date().isoformat()

    rExpired = []

    if get_setting_values(pDatabaseFile).get(LAST_CHECK_KEY) != vToday:
        # Noté d'abord : un échec n'est pas relancé à chaque tour du planificateur.
        save_setting_values(pDatabaseFile, {LAST_CHECK_KEY: vToday})

        rExpired = check_followed_offers(pDatabaseFile, pNow, pCheck)

    return rExpired


def describe_expired_offer(pOffer):
    """Résume une offre retirée : entreprise et étape de la candidature."""

    vParts = [
        pOffer.get("company"),
        STATUS_LABELS.get(pOffer["status"], pOffer["status"]),
    ]

    if pOffer.get("applied_at"):
        vParts.append(f"postulé le {format_date(pOffer['applied_at'])}")

    rText = " · ".join(vPart for vPart in vParts if vPart)

    return rText


def build_expired_offers_email(pOffers):
    """Construit le sujet, le texte et le HTML de l'e-mail des offres retirées."""

    rEmail = build_list_email(
        f"{APPLICATION_NAME} : {len(pOffers)} offre(s) suivie(s) retirée(s)",
        "Ces offres que vous suivez ne sont plus en ligne :",
        pOffers,
        describe_expired_offer,
        "offre(s) retirée(s)",
    )

    return rEmail


def list_withdrawn_offers(pDatabaseFile):
    """Retourne les offres suivies que leur site a retirées, pour les signaler."""

    rOffers = [
        {
            "source": vApplication["source"],
            "source_id": str(vApplication["source_id"]),
            "title": vApplication.get("title"),
            "company": vApplication.get("company"),
            "status": vApplication["status"],
        }
        for vApplication in get_applications_with_offers(
            pDatabaseFile, FOLLOWED_STATUSES
        )
        if vApplication.get("availability") == "expired"
    ]

    return rOffers


def count_alerts(pDatabaseFile, pNow):
    """Compte ce qui demande une action : relances dues et offres suivies retirées."""

    vApplications = get_applications_with_offers(pDatabaseFile, FOLLOWED_STATUSES)

    vFollowUps = sum(
        bool(vApplication.get("follow_up_date"))
        and vApplication["status"] in ("APPLIED", "INTERVIEW")
        and vApplication["follow_up_date"] <= pNow.isoformat()
        for vApplication in vApplications
    )
    vExpired = sum(
        vApplication.get("availability") == "expired" for vApplication in vApplications
    )

    rAlerts = {
        "follow_ups": vFollowUps,
        "expired": vExpired,
        "total": vFollowUps + vExpired,
        "text": f"{vFollowUps} relance(s) à faire, {vExpired} offre(s) suivie(s) retirée(s)",
    }

    return rAlerts
