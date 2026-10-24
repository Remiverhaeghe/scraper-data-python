"""Connexion à la base SQLite, décomptes quotidiens et application des
migrations (storage/migrations.py)
"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from storage.backup import backup_database
from storage.migrations import MIGRATIONS
from utils.logger import get_logger

logger = get_logger(__name__)


def connect_database(pDatabasePath):
    """Ouvre une connexion vers la base SQLite."""

    vDatabasePath = Path(pDatabasePath)

    vDatabasePath.parent.mkdir(parents=True, exist_ok=True)

    # Une connexion par opération, fermée aussitôt : le bureau, le web et le
    # planificateur peuvent partager le même fichier. « database is locked »
    # signale une écriture longue d'un autre processus, à relancer.
    vConnection = sqlite3.connect(vDatabasePath)

    rConnection = vConnection

    return rConnection


def get_database_version(pDatabasePath):
    """Retourne une empreinte qui change à chaque écriture validée, ou None.

    En journal classique (sans WAL), chaque écriture validée modifie la date et la
    taille du fichier, quel que soit le processus : bureau, web ou planificateur.
    """

    try:
        vStat = Path(pDatabasePath).stat()

    except OSError:
        return None

    rVersion = (vStat.st_mtime_ns, vStat.st_size)

    return rVersion


# Colonnes de date sur lesquelles un décompte quotidien est autorisé
DAILY_COUNT_COLUMNS = {
    ("job_offer", "first_seen_at"),
    ("job_application", "applied_at"),
    ("job_follow_up", "followed_up_at"),
    ("job_application", "responded_at"),
}


def count_by_day(pDatabasePath, pTable, pDateColumn, pDays, pNow=None):
    """Compte les lignes datées de chacun des derniers jours, jours vides compris.

    La table et la colonne sont insérées dans la requête : seules celles de
    DAILY_COUNT_COLUMNS sont acceptées.
    """

    if (pTable, pDateColumn) not in DAILY_COUNT_COLUMNS:
        raise ValueError(f"Décompte quotidien non autorisé : {pTable}.{pDateColumn}")

    vToday = (pNow or datetime.now()).date()
    vFirstDay = vToday - timedelta(days=pDays - 1)

    vConnection = connect_database(pDatabasePath)

    try:
        # Table et colonne vérifiées contre DAILY_COUNT_COLUMNS ci-dessus.
        vRows = vConnection.execute(
            f"SELECT substr({pDateColumn}, 1, 10) AS day, COUNT(*) "  # nosec B608
            f"FROM {pTable} WHERE {pDateColumn} >= ? GROUP BY day",
            (vFirstDay.isoformat(),),
        ).fetchall()

    finally:
        vConnection.close()

    vCounts = dict(vRows)

    rCounts = [
        (vDay, vCounts.get(vDay.isoformat(), 0))
        for vDay in (vFirstDay + timedelta(days=vOffset) for vOffset in range(pDays))
    ]

    return rCounts


def get_schema_version(pConnection):
    """Retourne la version du schéma enregistrée dans la base."""

    vCursor = pConnection.execute("PRAGMA user_version")

    rVersion = vCursor.fetchone()[0]

    return rVersion


def initialize_database(pDatabasePath):
    """Applique les migrations manquantes à la base."""

    vConnection = connect_database(pDatabasePath)

    try:
        # La version du schéma est stockée dans la base elle-même (PRAGMA
        # user_version) : seules les migrations plus récentes s'appliquent. Pour
        # diagnostiquer, ouvrir la base avec un outil SQLite et lire cette valeur.
        vCurrentVersion = get_schema_version(vConnection)

        # Une base déjà remplie est copiée avant d'être modifiée ; sans copie
        # réussie, l'exception interrompt le lancement et la base reste intacte.
        if 0 < vCurrentVersion < len(MIGRATIONS):
            backup_database(pDatabasePath, datetime.now(), f"avant-v{len(MIGRATIONS)}")

        for vVersion in range(vCurrentVersion + 1, len(MIGRATIONS) + 1):

            logger.info("Migration de la base vers la version %s", vVersion)

            # Chaque migration est atomique : en cas d'échec, la base reste
            # dans la version précédente.
            vConnection.execute("BEGIN")

            try:
                MIGRATIONS[vVersion - 1](vConnection)

                vConnection.execute(f"PRAGMA user_version = {vVersion}")

                vConnection.commit()

            except sqlite3.Error:
                vConnection.rollback()
                logger.exception("Échec de la migration vers la version %s", vVersion)
                raise

    finally:
        vConnection.close()
