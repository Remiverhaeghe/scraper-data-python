"""Sauvegarde et réinitialisation de la base de données"""

import sqlite3
from pathlib import Path

from storage.database import connect_database
from utils.logger import get_logger

logger = get_logger(__name__)

# Dossier des sauvegardes, à côté de la base
BACKUP_DIRECTORY_NAME = "backups"

# Ordre imposé par les clés étrangères : les tables qui référencent les offres
# sont vidées avant elles.
RESET_TABLES = (
    "job_follow_up",
    "job_application",
    "job_offer",
    "history",
    "app_setting",
    "saved_search",
    "duplicate_decision",
)


def backup_database(pDatabaseFile, pNow):
    """Copie la base dans le dossier des sauvegardes ; retourne le fichier créé."""

    vDatabaseFile = Path(pDatabaseFile)
    vDirectory = vDatabaseFile.parent / BACKUP_DIRECTORY_NAME
    vDirectory.mkdir(parents=True, exist_ok=True)

    rBackupFile = vDirectory / f"{vDatabaseFile.stem}-{pNow:%Y%m%d-%H%M%S}.db"

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

    return rBackupFile


def reset_database(pDatabaseFile, pNow):
    """Sauvegarde la base puis efface toutes ses données ; retourne la sauvegarde.

    Le schéma est conservé : l'application reste utilisable immédiatement.
    Sans sauvegarde réussie, rien n'est effacé.
    """

    rBackupFile = backup_database(pDatabaseFile, pNow)

    vConnection = connect_database(pDatabaseFile)

    try:
        for vTable in RESET_TABLES:
            # Nom de table issu de RESET_TABLES, une constante du code.
            vConnection.execute(f"DELETE FROM {vTable}")  # nosec B608

        vConnection.commit()

        # Libère la place occupée par les données effacées ; hors transaction.
        vConnection.execute("VACUUM")

    finally:
        vConnection.close()

    logger.warning(
        "Base réinitialisée, toutes les données ont été effacées ; sauvegarde : %s",
        rBackupFile.name,
    )

    return rBackupFile
