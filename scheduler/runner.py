"""Exécution de la recherche planifiée et envoi des notifications"""

import smtplib
from datetime import datetime

from job.application import process_jobs
from job.application_tracking import get_due_follow_ups
from job.notification import build_follow_ups_email, build_new_offers_email
from job.presentation import SCHEDULED_TRIGGER
from job.schedule import (
    FOLLOW_UP_REMINDER_KEY,
    describe_scheduled_search,
    is_schedule_due,
    load_schedule,
    mark_schedule_run,
)
from job.sources.aggregator import ScrapingCancelled
from job.sources.configuration import build_job_config, build_search_arguments
from storage.settings_repository import get_setting_values, save_setting_values
from utils.logger import get_logger
from utils.mailer import send_email

logger = get_logger(__name__)

# Délai entre deux vérifications de l'échéance, en secondes
POLL_SECONDS = 60


def notify_new_offers(pSchedule, pItems):
    """Envoie l'e-mail des nouvelles offres ; retourne True s'il est parti."""

    rSent = False

    vNewOffers = pItems[pItems["is_new"].astype(bool)] if not pItems.empty else pItems

    if not pSchedule["email"]:
        logger.info("Aucune adresse de notification : pas d'e-mail envoyé")

    elif vNewOffers.empty:
        logger.info("Aucune nouvelle offre : pas d'e-mail envoyé")

    else:
        vSubject, vText, vHtml = build_new_offers_email(
            vNewOffers.to_dict("records"),
            " · ".join(
                vPart for vPart in describe_scheduled_search(pSchedule) if vPart
            ),
        )

        try:
            send_email(pSchedule["email"], vSubject, vText, vHtml)
            rSent = True

        except (OSError, smtplib.SMTPException, ValueError) as vException:
            logger.error(
                "Échec de l'envoi de l'e-mail de notification : %s", vException
            )

    return rSent


def notify_follow_ups(pDatabaseFile, pSchedule, pNow):
    """Envoie le rappel des relances dues, une fois par jour ; retourne True s'il est parti."""

    rSent = False

    vToday = pNow.date().isoformat()

    if not pSchedule["email"]:
        logger.info("Aucune adresse de notification : pas de rappel de relances")

    elif get_setting_values(pDatabaseFile).get(FOLLOW_UP_REMINDER_KEY) == vToday:
        logger.info("Rappel des relances déjà envoyé aujourd'hui")

    else:
        vFollowUps = get_due_follow_ups(pDatabaseFile, pNow)

        if not vFollowUps:
            logger.info("Aucune relance due : pas de rappel envoyé")

        else:
            try:
                send_email(pSchedule["email"], *build_follow_ups_email(vFollowUps))

            except (OSError, smtplib.SMTPException, ValueError) as vException:
                logger.error("Échec de l'envoi du rappel des relances : %s", vException)

            else:
                save_setting_values(pDatabaseFile, {FOLLOW_UP_REMINDER_KEY: vToday})
                rSent = True

                logger.info("Rappel envoyé pour %s relance(s)", len(vFollowUps))

    return rSent


def run_due_search(pDatabaseFile, pNow, pCancelEvent=None):
    """Lance la recherche planifiée si elle est due ; retourne son résultat ou None."""

    vSchedule = load_schedule(pDatabaseFile)

    rResult = None

    if is_schedule_due(vSchedule, pNow):
        # Noté avant le lancement : une recherche en échec n'est pas relancée à
        # chaque vérification, mais à la prochaine échéance.
        mark_schedule_run(pDatabaseFile, pNow)

        vSearch = vSchedule["search"]

        logger.info(
            "Lancement de la recherche planifiée sur %s source(s)",
            len(vSearch["sources"]),
        )

        vConfig = build_job_config(
            build_search_arguments(vSearch["sources"], vSearch.get("criteria", {}))
        )

        rResult = process_jobs(
            vConfig, pCancelEvent=pCancelEvent, pTrigger=SCHEDULED_TRIGGER
        )

        notify_new_offers(vSchedule, rResult.items)
        notify_follow_ups(pDatabaseFile, vSchedule, pNow)

    return rResult


def run_forever(pDatabaseFile, pStopEvent, pPollSeconds=POLL_SECONDS):
    """Vérifie l'échéance à intervalle régulier jusqu'à la demande d'arrêt."""

    logger.info("Planificateur démarré, vérification toutes les %s s", pPollSeconds)

    while not pStopEvent.is_set():
        try:
            run_due_search(pDatabaseFile, datetime.now(), pStopEvent)

        except ScrapingCancelled:
            logger.info("Recherche planifiée interrompue par l'arrêt du planificateur")

        except Exception:
            logger.exception("Erreur inattendue pendant la recherche planifiée")

        pStopEvent.wait(pPollSeconds)

    logger.info("Planificateur arrêté")
