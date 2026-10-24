"""Réinitialisation de la base et purge des offres, après sauvegarde"""

from storage.attachments import get_attachment_directory
from storage.backup import BACKUP_DIRECTORY_NAME, backup_database
from storage.database import connect_database
from utils.logger import get_logger

logger = get_logger(__name__)

# Ordre imposé par les clés étrangères : les tables qui référencent les offres
# sont vidées avant elles. Les questions de révision importées, leurs thèmes,
# schémas et guides ne sont pas des données de recherche : elles sont gardées.
RESET_TABLES = (
    "quiz_answer",
    "challenge_attempt",
    "git_level_result",
    "job_attachment",
    "interview_note",
    "job_follow_up",
    "application_history",
    "job_application",
    "job_offer",
    "history",
    "saved_search",
    "duplicate_decision",
)

# Réglages gardés avec les questions : la liste des questions signalées comme
# douteuses (FLAGGED_KEY de job/quiz.py), sans quoi elles reviendraient.
KEPT_SETTINGS = ("quiz_flagged",)


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

        vConnection.execute(
            "DELETE FROM app_setting WHERE key NOT IN "
            f"({', '.join('?' * len(KEPT_SETTINGS))})",  # nosec B608
            KEPT_SETTINGS,
        )

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


def get_purgeable_offers(pDatabaseFile):
    """Retourne les offres sans candidature, relance, pièce jointe ni journal d'entretien."""

    vConnection = connect_database(pDatabaseFile)

    try:
        vRows = vConnection.execute("""
            SELECT source, source_id, title, company, first_seen_at, last_seen_at
            FROM job_offer AS o
            WHERE NOT EXISTS (
                SELECT 1 FROM job_application AS a
                WHERE a.source = o.source AND a.source_id = o.source_id
            )
            AND NOT EXISTS (
                SELECT 1 FROM job_follow_up AS f
                WHERE f.source = o.source AND f.source_id = o.source_id
            )
            AND NOT EXISTS (
                SELECT 1 FROM job_attachment AS j
                WHERE j.source = o.source AND j.source_id = o.source_id
            )
            AND NOT EXISTS (
                SELECT 1 FROM interview_note AS n
                WHERE n.source = o.source AND n.source_id = o.source_id
            )
            ORDER BY first_seen_at DESC
            """).fetchall()

    finally:
        vConnection.close()

    rOffers = [
        {
            "source": vSource,
            "source_id": vSourceId,
            "title": vTitle,
            "company": vCompany,
            "first_seen_at": vFirstSeenAt,
            "last_seen_at": vLastSeenAt,
        }
        for vSource, vSourceId, vTitle, vCompany, vFirstSeenAt, vLastSeenAt in vRows
    ]

    return rOffers


def delete_offers(pDatabaseFile, pKeys, pNow):
    """Sauvegarde la base puis supprime les offres ; retourne la sauvegarde.

    Sans sauvegarde réussie, rien n'est supprimé.
    """

    rBackupFile = backup_database(pDatabaseFile, pNow, "avant-purge")

    vConnection = connect_database(pDatabaseFile)

    try:
        vConnection.executemany(
            "DELETE FROM job_offer WHERE source = ? AND source_id = ?", list(pKeys)
        )
        vConnection.commit()

    finally:
        vConnection.close()

    logger.info(
        "%s offre(s) supprimée(s) après sauvegarde : %s", len(pKeys), rBackupFile.name
    )

    return rBackupFile
