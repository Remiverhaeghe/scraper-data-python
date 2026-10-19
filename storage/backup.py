"""Sauvegarde de la base de données et rotation des sauvegardes"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from config import AUTO_BACKUP_INTERVAL_HOURS, AUTO_BACKUP_KEEP_COUNT, BACKUP_KEEP_COUNT
from utils.logger import get_logger

logger = get_logger(__name__)

# Dossier des sauvegardes, à côté de la base
BACKUP_DIRECTORY_NAME = "backups"

# Suffixe des sauvegardes automatiques : elles tournent entre elles, sans évincer
# celles faites avant une opération risquée.
AUTO_BACKUP_REASON = "auto"


def backup_database(pDatabaseFile, pNow, pReason=None):
    """Copie la base dans le dossier des sauvegardes ; retourne le fichier créé.

    pReason complète le nom du fichier, par exemple « avant-v9 ».
    """

    vDatabaseFile = Path(pDatabaseFile)
    vDirectory = vDatabaseFile.parent / BACKUP_DIRECTORY_NAME
    vDirectory.mkdir(parents=True, exist_ok=True)

    vSuffix = f"-{pReason}" if pReason else ""

    rBackupFile = vDirectory / f"{vDatabaseFile.stem}-{pNow:%Y%m%d-%H%M%S}{vSuffix}.db"

    # L'API de sauvegarde de SQLite produit une copie cohérente, même si une autre
    # application écrit dans la base au même moment, ce que ne garantit pas une
    # simple copie de fichier.
    vSource = sqlite3.connect(vDatabaseFile)
    vTarget = sqlite3.connect(rBackupFile)

    try:
        vSource.backup(vTarget)

    finally:
        vTarget.close()
        vSource.close()

    logger.info("Sauvegarde de la base créée : %s", rBackupFile.name)

    vAutomatic = pReason == AUTO_BACKUP_REASON

    purge_backups(
        vDatabaseFile,
        AUTO_BACKUP_KEEP_COUNT if vAutomatic else BACKUP_KEEP_COUNT,
        vAutomatic,
    )

    return rBackupFile


def list_backups(pDatabaseFile, pAutomatic=False):
    """Retourne les sauvegardes automatiques, ou les autres, les plus récentes en tête."""

    vDatabaseFile = Path(pDatabaseFile)
    vDirectory = vDatabaseFile.parent / BACKUP_DIRECTORY_NAME

    # La date est dans le nom : l'ordre alphabétique est l'ordre chronologique.
    rBackups = [
        vBackupFile
        for vBackupFile in sorted(
            vDirectory.glob(f"{vDatabaseFile.stem}-*.db"), reverse=True
        )
        if vBackupFile.stem.endswith(f"-{AUTO_BACKUP_REASON}") == pAutomatic
    ]

    return rBackups


def purge_backups(pDatabaseFile, pKeepCount=BACKUP_KEEP_COUNT, pAutomatic=False):
    """Supprime les sauvegardes les plus anciennes ; retourne le nombre supprimé."""

    rDeletedCount = 0

    for vBackupFile in list_backups(pDatabaseFile, pAutomatic)[pKeepCount:]:
        try:
            vBackupFile.unlink()

        except OSError:
            # Un fichier ouvert ailleurs est laissé en place, au prochain passage.
            logger.warning("Sauvegarde non supprimée : %s", vBackupFile.name)

        else:
            rDeletedCount += 1

    if rDeletedCount:
        logger.info("Anciennes sauvegardes supprimées : %s", rDeletedCount)

    return rDeletedCount


def get_last_auto_backup_time(pDatabaseFile):
    """Retourne la date de la dernière sauvegarde automatique, lue dans son nom."""

    vStem = Path(pDatabaseFile).stem

    rTime = None

    for vBackupFile in list_backups(pDatabaseFile, pAutomatic=True):
        vStamp = vBackupFile.stem[len(vStem) + 1 : -len(AUTO_BACKUP_REASON) - 1]

        try:
            rTime = datetime.strptime(vStamp, "%Y%m%d-%H%M%S")

        except ValueError:
            continue

        break

    return rTime


def run_due_backup(pDatabaseFile, pNow):
    """Sauvegarde la base si la dernière sauvegarde automatique est trop ancienne.

    Retourne le fichier créé, ou None. Un échec est journalisé sans interrompre
    l'appelant : l'application et le planificateur continuent.
    """

    rBackupFile = None

    try:
        vLastTime = get_last_auto_backup_time(pDatabaseFile)

        if vLastTime is None or pNow - vLastTime >= timedelta(
            hours=AUTO_BACKUP_INTERVAL_HOURS
        ):
            rBackupFile = backup_database(pDatabaseFile, pNow, AUTO_BACKUP_REASON)

    except (OSError, sqlite3.Error):
        logger.exception("Échec de la sauvegarde automatique de la base")

    return rBackupFile
