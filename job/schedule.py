"""Réglages et échéance de la recherche planifiée"""

import json
import re
from datetime import datetime, timedelta

from job.presentation import describe_search, describe_sources
from storage.settings_repository import get_setting_values, save_setting_values
from utils.logger import get_logger

logger = get_logger(__name__)

# Fréquences proposées, en heures
SCHEDULE_INTERVALS = (1, 3, 6, 12, 24)
DEFAULT_INTERVAL_HOURS = 6

ENABLED_KEY = "schedule_enabled"
INTERVAL_KEY = "schedule_interval_hours"
SEARCH_KEY = "schedule_search"
LAST_RUN_KEY = "schedule_last_run"
EMAIL_KEY = "notification_email"

# Demande de recherche immédiate déposée depuis le web, traitée par le planificateur
RUN_REQUEST_KEY = "schedule_run_requested"

# Jour du dernier rappel de relances envoyé : un seul e-mail par jour
FOLLOW_UP_REMINDER_KEY = "follow_up_reminder_sent"

# Contrôle de forme volontairement simple : seul l'envoi prouve que l'adresse existe.
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def parse_interval(pValue):
    """Retourne la fréquence enregistrée, ou celle par défaut si elle est invalide."""

    try:
        rInterval = int(pValue)

    except (TypeError, ValueError):
        rInterval = DEFAULT_INTERVAL_HOURS

    if rInterval not in SCHEDULE_INTERVALS:
        rInterval = DEFAULT_INTERVAL_HOURS

    return rInterval


def parse_search(pValue):
    """Retourne la recherche enregistrée, ou None si elle est absente ou illisible."""

    rSearch = None

    if pValue:
        try:
            rSearch = json.loads(pValue)

        except ValueError:
            logger.warning("Recherche planifiée enregistrée illisible : ignorée")

    return rSearch


def parse_date(pValue):
    """Retourne la date enregistrée, ou None si elle est absente ou illisible."""

    try:
        rDate = datetime.fromisoformat(pValue) if pValue else None

    except ValueError:
        rDate = None

    return rDate


def load_schedule(pDatabaseFile):
    """Retourne l'état de la planification et de la notification."""

    vValues = get_setting_values(pDatabaseFile)

    rSchedule = {
        "enabled": vValues.get(ENABLED_KEY) == "1",
        "interval_hours": parse_interval(vValues.get(INTERVAL_KEY)),
        "search": parse_search(vValues.get(SEARCH_KEY)),
        "last_run": parse_date(vValues.get(LAST_RUN_KEY)),
        "email": vValues.get(EMAIL_KEY) or None,
        "run_requested": parse_date(vValues.get(RUN_REQUEST_KEY)),
    }

    return rSchedule


def save_scheduled_search(pDatabaseFile, pSources, pCriteria):
    """Enregistre les sources et les critères que lancera le planificateur."""

    vCriteria = {
        vName: vValue for vName, vValue in pCriteria.items() if vValue is not None
    }

    save_setting_values(
        pDatabaseFile,
        {
            SEARCH_KEY: json.dumps(
                {"sources": list(pSources), "criteria": vCriteria}, ensure_ascii=False
            )
        },
    )

    logger.info("Recherche planifiée enregistrée sur %s source(s)", len(pSources))


def save_schedule_options(pDatabaseFile, pEnabled, pIntervalHours):
    """Enregistre l'activation et la fréquence ; retourne les erreurs éventuelles."""

    rErrors = []

    if pIntervalHours not in SCHEDULE_INTERVALS:
        rErrors.append("Fréquence non proposée.")

    if pEnabled and load_schedule(pDatabaseFile)["search"] is None:
        rErrors.append("Enregistrez d'abord une recherche depuis la page Recherche.")

    if not rErrors:
        save_setting_values(
            pDatabaseFile,
            {ENABLED_KEY: "1" if pEnabled else "0", INTERVAL_KEY: pIntervalHours},
        )

        logger.info(
            "Planification %s, toutes les %s heure(s)",
            "activée" if pEnabled else "désactivée",
            pIntervalHours,
        )

    return rErrors


def save_notification_email(pDatabaseFile, pEmail):
    """Enregistre l'adresse des notifications ; retourne les erreurs éventuelles."""

    vEmail = (pEmail or "").strip()

    rErrors = []

    if vEmail and not EMAIL_PATTERN.match(vEmail):
        rErrors.append("Adresse e-mail invalide.")
    else:
        save_setting_values(pDatabaseFile, {EMAIL_KEY: vEmail})

        logger.info("Notifications e-mail %s", "activées" if vEmail else "désactivées")

    return rErrors


def mark_schedule_run(pDatabaseFile, pRunAt):
    """Note l'heure de lancement de la recherche planifiée et efface la demande."""

    save_setting_values(
        pDatabaseFile, {LAST_RUN_KEY: pRunAt.isoformat(), RUN_REQUEST_KEY: ""}
    )


def request_immediate_run(pDatabaseFile, pNow):
    """Demande au planificateur de lancer la recherche ; retourne les erreurs."""

    rErrors = []

    if load_schedule(pDatabaseFile)["search"] is None:
        rErrors.append("Enregistrez d'abord une recherche depuis la page Recherche.")
    else:
        save_setting_values(pDatabaseFile, {RUN_REQUEST_KEY: pNow.isoformat()})

        logger.info("Recherche immédiate demandée au planificateur")

    return rErrors


def get_next_run(pSchedule, pNow):
    """Retourne la prochaine exécution prévue, ou None si rien n'est planifié."""

    rNextRun = None

    if pSchedule["enabled"] and pSchedule["search"] is not None:
        rNextRun = pNow

        if pSchedule["last_run"] is not None:
            rNextRun = pSchedule["last_run"] + timedelta(
                hours=pSchedule["interval_hours"]
            )

    return rNextRun


def is_schedule_due(pSchedule, pNow):
    """Indique si la recherche planifiée doit être lancée maintenant."""

    vNextRun = get_next_run(pSchedule, pNow)

    # Une demande immédiate est traitée même si la planification est désactivée.
    rDue = (vNextRun is not None and vNextRun <= pNow) or (
        pSchedule.get("run_requested") is not None and pSchedule["search"] is not None
    )

    return rDue


def describe_scheduled_search(pSchedule):
    """Résume la recherche planifiée : critères puis sources."""

    vSearch = pSchedule["search"]

    rDescription = ("Aucune recherche enregistrée", "")

    if vSearch is not None:
        vParameters = {**vSearch.get("criteria", {}), "sources": vSearch["sources"]}

        rDescription = (
            describe_search(vParameters) or "Sans critère",
            describe_sources(vParameters),
        )

    return rDescription


def format_interval(pIntervalHours):
    """Retourne le libellé d'une fréquence, en heures."""

    rLabel = (
        "Toutes les heures"
        if pIntervalHours == 1
        else f"Toutes les {pIntervalHours} heures"
    )

    return rLabel


def describe_schedule_runs(pSchedule, pNow):
    """Résume l'état de la planification : dernière et prochaine exécution."""

    vNextRun = get_next_run(pSchedule, pNow)
    vLastRun = pSchedule["last_run"]

    vLast = f"{vLastRun:%d/%m/%Y à %H:%M}" if vLastRun else "jamais"

    if pSchedule.get("run_requested") is not None:
        rText = (
            f"Recherche demandée le {pSchedule['run_requested']:%d/%m/%Y à %H:%M}, "
            "lancée à la prochaine vérification du planificateur (python -m "
            f"scheduler). Dernière exécution : {vLast}."
        )
    elif vNextRun is None:
        rText = f"Planification désactivée. Dernière exécution : {vLast}."
    elif vNextRun <= pNow:
        rText = (
            f"Dernière exécution : {vLast}. Prochaine : dès la prochaine "
            "vérification du planificateur."
        )
    else:
        rText = (
            f"Dernière exécution : {vLast}. Prochaine : {vNextRun:%d/%m/%Y à %H:%M}."
        )

    return rText
