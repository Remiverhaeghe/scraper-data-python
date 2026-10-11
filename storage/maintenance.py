"""Réinitialisation de la base de données, après sauvegarde"""

from storage.attachments import get_attachment_directory
from storage.backup import BACKUP_DIRECTORY_NAME, backup_database
from storage.database import connect_database
from utils.logger import get_logger

logger = get_logger(__name__)

# Ordre imposé par les clés étrangères : les tables qui référencent les offres
# sont vidées avant elles.
RESET_TABLES = (
    "quiz_answer",
    "job_attachment",
    "job_follow_up",
    "job_application",
    "job_offer",
    "history",
    "app_setting",
    "saved_search",
    "duplicate_decision",
)


def move_attachments(pDatabaseFile, pNow):
    """Range les pièces jointes avec les sauvegardes plutôt que de les effacer."""

    vDirectory = get_attachment_directory(pDatabaseFile)

    if vDirectory.is_dir() and any(vDirectory.iterdir()):
        vTarget = (
            vDirectory.parent
            / BACKUP_DIRECTORY_NAME
            / f"{vDirectory.name}-{pNow:%Y%m%d-%H%M%S}"
        )
        vTarget.parent.mkdir(parents=True, exist_ok=True)

        vDirectory.rename(vTarget)

        logger.info("Pièces jointes déplacées dans %s", vTarget.name)


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

    move_attachments(pDatabaseFile, pNow)

    logger.warning(
        "Base réinitialisée, toutes les données ont été effacées ; sauvegarde : %s",
        rBackupFile.name,
    )

    return rBackupFile
