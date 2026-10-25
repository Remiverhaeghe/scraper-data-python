"""Restauration éprouvée : la dernière sauvegarde, et la dernière copie du NAS,
sont restaurées à l'essai chaque mois

Une sauvegarde vérifiée à sa création peut encore échouer à la restauration
(version, tables, clé de chiffrement). L'essai se fait dans un dossier
temporaire : la vraie base n'est jamais touchée.
"""

import shutil
import sqlite3
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from config import BACKUP_ENCRYPTION_KEY, BACKUP_NAS_DIRECTORY
from storage.archive import check_database
from storage.backup import ENCRYPTED_SUFFIX, list_backups, list_nas_copies
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


def try_restored_file(pDatabaseFile, pRestored, pName):
    """Contrôle une base restaurée à l'essai ; retourne (réussite, message)."""

    try:
        check_database(pRestored, "Restauration impossible")
        vRestored = count_offers(pRestored)

    except ValueError as vException:
        return (False, f"{pName} : {vException}")

    vCurrent = count_offers(pDatabaseFile)

    rResult = (
        (False, f"{pName} : {vRestored} offre(s) seulement, contre {vCurrent} en base")
        if vCurrent and vRestored < vCurrent * MIN_OFFER_SHARE
        else (True, f"{pName} restaurée à l'essai : {vRestored} offre(s)")
    )

    return rResult


def check_restore(pDatabaseFile):
    """Restaure la dernière sauvegarde à l'essai ; retourne (réussite, message)."""

    vBackup = next(iter(list_backups(pDatabaseFile)), None)

    if vBackup is None:
        return (False, "Aucune sauvegarde à restaurer")

    with tempfile.TemporaryDirectory() as vDirectory:
        vCopy = Path(vDirectory) / "essai.db"
        shutil.copy2(vBackup, vCopy)

        rResult = try_restored_file(pDatabaseFile, vCopy, vBackup.name)

    logger.info(
        "Essai de restauration %s : %s",
        "réussi" if rResult[0] else "en échec",
        rResult[1],
    )

    return rResult


def check_nas_restore(pDatabaseFile, pNasDirectory=None, pKey=BACKUP_ENCRYPTION_KEY):
    """Restaure à l'essai la dernière copie du NAS, déchiffrée si besoin ; retourne
    (réussite, message), ou None sans NAS configuré.
    """

    vNasDirectory = pNasDirectory or BACKUP_NAS_DIRECTORY

    if vNasDirectory is None:
        return None

    try:
        vCopy = next(iter(list_nas_copies(pDatabaseFile, vNasDirectory)), None)

    except OSError as vException:
        return (False, f"NAS injoignable : {vException}")

    if vCopy is None:
        return (False, "Aucune copie sur le NAS")

    vEncrypted = vCopy.name.endswith(ENCRYPTED_SUFFIX)

    if vEncrypted and not pKey:
        return (False, f"{vCopy.name} : BACKUP_ENCRYPTION_KEY manquante dans .env")

    with tempfile.TemporaryDirectory() as vDirectory:
        vRestored = Path(vDirectory) / "essai.db"

        try:
            vContent = vCopy.read_bytes()
            vRestored.write_bytes(
                Fernet(pKey).decrypt(vContent) if vEncrypted else vContent
            )

        except InvalidToken:
            return (False, f"{vCopy.name} : chiffrée avec une autre clé")

        except OSError as vException:
            return (False, f"{vCopy.name} illisible : {vException}")

        rResult = try_restored_file(pDatabaseFile, vRestored, vCopy.name)

    logger.info(
        "Essai de restauration de la copie du NAS %s : %s",
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
    vNas = check_nas_restore(pDatabaseFile)

    if vNas is not None:
        vSuccess = vSuccess and vNas[0]
        vMessage += f" ; NAS : {vNas[1]}"

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
