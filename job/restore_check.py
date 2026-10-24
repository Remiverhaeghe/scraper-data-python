"""Restauration éprouvée : la dernière sauvegarde est restaurée à l'essai chaque mois

Une sauvegarde vérifiée à sa création peut encore échouer à la restauration
(version, tables). L'essai se fait dans un dossier temporaire : la vraie base
n'est jamais touchée.
"""

import shutil
import sqlite3
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from storage.archive import check_database
from storage.backup import list_backups
from storage.settings_repository import load_json_setting, save_json_setting
from utils.logger import get_logger

logger = get_logger(__name__)

RESTORE_CHECK_KEY = "last_restore_check"
RESTORE_CHECK_DAYS = 30

# Part des offres de la base qu'une sauvegarde récente doit contenir au moins
MIN_OFFER_SHARE = 0.5


def count_offers(pDatabaseFile):
    """Retourne le nombre d'offres d'une base, ouverte en lecture seule."""

    vConnection = sqlite3.connect(
        Path(pDatabaseFile).resolve().as_uri() + "?mode=ro", uri=True
    )

    try:
        rCount = vConnection.execute("SELECT COUNT(*) FROM job_offer").fetchone()[0]

    finally:
        vConnection.close()

    return rCount


def check_restore(pDatabaseFile):
    """Restaure la dernière sauvegarde à l'essai ; retourne (réussite, message)."""

    vBackup = next(iter(list_backups(pDatabaseFile)), None)

    if vBackup is None:
        return (False, "Aucune sauvegarde à restaurer")

    with tempfile.TemporaryDirectory() as vDirectory:
        vCopy = Path(vDirectory) / "essai.db"
        shutil.copy2(vBackup, vCopy)

        try:
            check_database(vCopy, "Restauration impossible")
            vRestored = count_offers(vCopy)

        except ValueError as vException:
            return (False, f"{vBackup.name} : {vException}")

    vCurrent = count_offers(pDatabaseFile)

    if vCurrent and vRestored < vCurrent * MIN_OFFER_SHARE:
        rResult = (
            False,
            f"{vBackup.name} : {vRestored} offre(s) seulement, contre {vCurrent} en base",
        )
    else:
        rResult = (True, f"{vBackup.name} restaurée à l'essai : {vRestored} offre(s)")

    logger.info(
        "Essai de restauration %s : %s",
        "réussi" if rResult[0] else "en échec",
        rResult[1],
    )

    return rResult


def run_due_restore_check(pDatabaseFile, pNow):
    """Fait l'essai de restauration si le dernier date de plus de RESTORE_CHECK_DAYS jours."""

    vLast = load_json_setting(pDatabaseFile, RESTORE_CHECK_KEY, {}, dict)

    if vLast.get("date") and pNow - datetime.fromisoformat(vLast["date"]) < timedelta(
        days=RESTORE_CHECK_DAYS
    ):
        return None

    vSuccess, vMessage = check_restore(pDatabaseFile)

    rResult = {
        "date": pNow.isoformat(timespec="seconds"),
        "success": vSuccess,
        "message": vMessage,
    }
    save_json_setting(pDatabaseFile, RESTORE_CHECK_KEY, rResult)

    return rResult


def load_restore_check(pDatabaseFile):
    """Retourne le résultat du dernier essai de restauration, vide sans essai."""

    rResult = load_json_setting(pDatabaseFile, RESTORE_CHECK_KEY, {}, dict)

    return rResult
