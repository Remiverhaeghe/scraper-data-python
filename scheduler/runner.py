"""Exécution de la recherche planifiée et envoi des notifications"""

import smtplib
import sqlite3
from datetime import datetime

import pandas as pd

from job.application import process_jobs
from job.application_tracking import get_due_follow_ups
from job.followed_availability import (
    build_expired_offers_email,
    run_due_followed_check,
)
from job.interview_reminder import (
    build_reminder_email,
    get_interviews_to_remind,
    mark_reminded,
)
from job.notification import build_follow_ups_email, build_new_offers_email
from job.preparation import score_offers
from job.presentation import SCHEDULED_TRIGGER, clean_missing_values
from job.profile import load_profile
from job.schedule import (
    FOLLOW_UP_REMINDER_KEY,
    describe_extra_searches,
    describe_scheduled_search,
    get_scheduled_searches,
    is_schedule_due,
    load_schedule,
    mark_schedule_run,
)
from job.sources.aggregator import ScrapingCancelled
from job.sources.configuration import build_job_config, build_search_arguments
from job.weekly_digest import (
    build_digest_email,
    build_weekly_digest,
    is_digest_due,
    mark_digest_sent,
)
from storage.backup import run_due_backup
from storage.settings_repository import get_setting_values, save_setting_values
from utils.logger import get_logger
from utils.mailer import send_email

logger = get_logger(__name__)

# Délai entre deux vérifications de l'échéance, en secondes
POLL_SECONDS = 60


def select_alert_offers(pDatabaseFile, pOffers, pMinScore):
    """Garde les offres au-dessus du score minimal, les mieux notées en premier.

    Sans compétence dans le profil, aucun score n'existe : tout est envoyé.
    """

    score_offers(pOffers, load_profile(pDatabaseFile))

    rOffers = pOffers

    if pMinScore and rOffers and rOffers[0]["match_score"] is None:
        logger.warning(
            "Score minimal des alertes ignoré : aucune compétence dans le profil"
        )

    elif pMinScore:
        rOffers = sorted(
            (vOffer for vOffer in rOffers if vOffer["match_score"] >= pMinScore),
            key=lambda pOffer: pOffer["match_score"],
            reverse=True,
        )

        logger.info(
            "Alertes : %s offre(s) sur %s atteignent %s %% de correspondance",
            len(rOffers),
            len(pOffers),
            pMinScore,
        )

    return rOffers


def notify_new_offers(pDatabaseFile, pSchedule, pItems):
    """Envoie l'e-mail des nouvelles offres ; retourne True s'il est parti."""

    rSent = False

    vNewOffers = (
        [
            clean_missing_values(vOffer)
            for vOffer in pItems[pItems["is_new"].astype(bool)].to_dict("records")
        ]
        if not pItems.empty
        else []
    )
    vOffers = (
        select_alert_offers(pDatabaseFile, vNewOffers, pSchedule["min_score"])
        if pSchedule["email"] and vNewOffers
        else []
    )

    if not pSchedule["email"]:
        logger.info("Aucune adresse de notification : pas d'e-mail envoyé")

    elif not vNewOffers:
        logger.info("Aucune nouvelle offre : pas d'e-mail envoyé")

    elif not vOffers:
        logger.info("Aucune nouvelle offre au-dessus du score minimal : pas d'e-mail")

    else:
        vSubject, vText, vHtml = build_new_offers_email(
            vOffers,
            " · ".join(
                vPart
                for vPart in (
                    *describe_scheduled_search(pSchedule),
                    describe_extra_searches(pSchedule),
                )
                if vPart
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

        rResult = []

        for vSearch in get_scheduled_searches(pDatabaseFile, vSchedule):
            vResult = run_search(vSearch, pCancelEvent)

            if vResult is not None:
                rResult.append(vResult)

        notify_new_offers(
            pDatabaseFile,
            vSchedule,
            merge_items([vResult.items for vResult in rResult]),
        )
        notify_follow_ups(pDatabaseFile, vSchedule, pNow)

    return rResult


def run_search(pSearch, pCancelEvent):
    """Lance une recherche ; retourne son résultat, ou None si elle a échoué."""

    logger.info(
        "Lancement de « %s » sur %s source(s)",
        pSearch["name"],
        len(pSearch["sources"]),
    )

    vConfig = build_job_config(
        build_search_arguments(pSearch["sources"], pSearch.get("criteria", {}))
    )

    rResult = None

    # Une recherche en échec n'empêche pas les suivantes ni la notification.
    try:
        rResult = process_jobs(
            vConfig, pCancelEvent=pCancelEvent, pTrigger=SCHEDULED_TRIGGER
        )

    except ScrapingCancelled:
        raise

    except Exception:
        logger.exception("Échec de la recherche planifiée « %s »", pSearch["name"])

    return rResult


def merge_items(pItemsList):
    """Rassemble les offres de plusieurs recherches, chaque adresse une seule fois."""

    vItemsList = [vItems for vItems in pItemsList if not vItems.empty]

    rItems = pd.DataFrame()

    if len(vItemsList) == 1:
        rItems = vItemsList[0]

    elif vItemsList:
        # Une offre nouvelle pour la première recherche est déjà connue de la
        # suivante : la version nouvelle passe en tête pour être gardée.
        vItems = pd.concat(vItemsList, ignore_index=True).sort_values(
            "is_new", ascending=False, kind="stable"
        )
        vDuplicated = vItems["url"].notna() & vItems.duplicated("url")

        rItems = vItems[~vDuplicated].sort_index()

    return rItems


def check_followed_offers_daily(pDatabaseFile, pNow):
    """Vérifie une fois par jour les offres suivies et signale celles retirées."""

    rSent = False

    vExpired = run_due_followed_check(pDatabaseFile, pNow)
    vEmail = load_schedule(pDatabaseFile)["email"]

    if vExpired and vEmail:
        send_email(vEmail, *build_expired_offers_email(vExpired))
        rSent = True

        logger.info("Alerte envoyée pour %s offre(s) retirée(s)", len(vExpired))

    return rSent


def send_weekly_digest(pDatabaseFile, pNow):
    """Envoie le récapitulatif de la semaine s'il n'est pas encore parti."""

    rSent = False

    vEmail = load_schedule(pDatabaseFile)["email"]

    if vEmail and is_digest_due(pDatabaseFile, pNow):
        send_email(
            vEmail, *build_digest_email(build_weekly_digest(pDatabaseFile, pNow))
        )
        mark_digest_sent(pDatabaseFile, pNow)
        rSent = True

    return rSent


def send_interview_reminders(pDatabaseFile, pNow):
    """Envoie le rappel de chaque entretien des prochaines 24 heures ; retourne leur nombre."""

    rCount = 0

    vEmail = load_schedule(pDatabaseFile)["email"]

    for vApplication in get_interviews_to_remind(pDatabaseFile, pNow) if vEmail else []:
        send_email(vEmail, *build_reminder_email(pDatabaseFile, vApplication))
        mark_reminded(pDatabaseFile, vApplication)
        rCount += 1

        logger.info(
            "Rappel d'entretien envoyé : %s %s",
            vApplication["source"],
            vApplication["source_id"],
        )

    return rCount


# Tâches de chaque tour du planificateur, avant la recherche : chacune vérifie
# elle-même son échéance. Une nouvelle tâche s'ajoute ici, sans toucher la boucle.
BACKGROUND_TASKS = (
    ("sauvegarde automatique", run_due_backup),
    ("vérification des offres suivies", check_followed_offers_daily),
    ("récapitulatif hebdomadaire", send_weekly_digest),
    ("rappels d'entretien", send_interview_reminders),
)

# Erreurs attendues d'une tâche : disque, base, envoi d'e-mail ou réglage invalide
TASK_ERRORS = (OSError, sqlite3.Error, smtplib.SMTPException, ValueError)


def run_background_tasks(pDatabaseFile, pNow, pTasks=None):
    """Exécute les tâches de fond ; une tâche en échec n'empêche pas les suivantes."""

    for vName, vTask in BACKGROUND_TASKS if pTasks is None else pTasks:
        try:
            vTask(pDatabaseFile, pNow)

        except TASK_ERRORS as vException:
            logger.error("Échec de la tâche « %s » : %s", vName, vException)


def run_forever(pDatabaseFile, pStopEvent, pPollSeconds=POLL_SECONDS):
    """Vérifie l'échéance à intervalle régulier jusqu'à la demande d'arrêt."""

    logger.info("Planificateur démarré, vérification toutes les %s s", pPollSeconds)

    while not pStopEvent.is_set():
        run_background_tasks(pDatabaseFile, datetime.now())

        try:
            run_due_search(pDatabaseFile, datetime.now(), pStopEvent)

        except ScrapingCancelled:
            logger.info("Recherche planifiée interrompue par l'arrêt du planificateur")

        except Exception:
            logger.exception("Erreur inattendue pendant la recherche planifiée")

        pStopEvent.wait(pPollSeconds)

    logger.info("Planificateur arrêté")
