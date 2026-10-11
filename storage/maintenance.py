"""Réinitialisation de la base de données, après sauvegarde"""

from storage.backup import backup_database
from storage.database import connect_database
from utils.logger import get_logger

logger = get_logger(__name__)

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
