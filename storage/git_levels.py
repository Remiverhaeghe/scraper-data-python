"""Bac à sable Git : meilleur résultat de chaque niveau réussi"""

from storage.database import connect_database
from utils.logger import get_logger

logger = get_logger(__name__)


def save_git_level_result(pDatabaseFile, pLevel, pCommandCount, pNow):
    """Enregistre un niveau réussi, en ne gardant que le plus petit nombre de commandes."""

    vConnection = connect_database(pDatabaseFile)

    try:
        vConnection.execute(
            """
            INSERT INTO git_level_result (level, best_count, completed_at)
            VALUES (?, ?, ?)
            ON CONFLICT(level) DO UPDATE SET
                best_count = MIN(best_count, excluded.best_count),
                completed_at = excluded.completed_at
            """,
            (pLevel, pCommandCount, pNow.isoformat()),
        )
        vConnection.commit()

    finally:
        vConnection.close()

    logger.info("Niveau Git %s réussi en %s commande(s)", pLevel, pCommandCount)


def get_git_level_results(pDatabaseFile):
    """Retourne le meilleur nombre de commandes de chaque niveau réussi."""

    vConnection = connect_database(pDatabaseFile)

    try:
        rResults = dict(
            vConnection.execute("SELECT level, best_count FROM git_level_result")
        )

    finally:
        vConnection.close()

    return rResults
