"""Sauvegarde de la base de données et rotation des sauvegardes"""

import sqlite3
from pathlib import Path

from config import BACKUP_KEEP_COUNT
from utils.logger import get_logger

logger = get_logger(__name__)

# Dossier des sauvegardes, à côté de la base
BACKUP_DIRECTORY_NAME = "backups"


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

    purge_backups(vDatabaseFile)

    return rBackupFile


def purge_backups(pDatabaseFile, pKeepCount=BACKUP_KEEP_COUNT):
    """Supprime les sauvegardes les plus anciennes ; retourne le nombre supprimé."""

    vDatabaseFile = Path(pDatabaseFile)
    vDirectory = vDatabaseFile.parent / BACKUP_DIRECTORY_NAME

    # La date est dans le nom : l'ordre alphabétique est l'ordre chronologique.
    vBackups = sorted(vDirectory.glob(f"{vDatabaseFile.stem}-*.db"), reverse=True)

    rDeletedCount = 0

    for vBackupFile in vBackups[pKeepCount:]:
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
