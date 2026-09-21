# ============================================================================
# Persistance des entrées d'historique dans SQLite
# ============================================================================


from datetime import datetime

from scraper.history import HistoryEntry
from storage.database import connect_database


HISTORY_TABLE = "history"


def initialize_history(pDatabasePath):
    """
    Crée et met à jour la table d'historique si nécessaire.

    :param pDatabasePath: Chemin vers la base SQLite.
    """

    vConnection = connect_database(
        pDatabasePath
    )

    vConnection.execute(
        """
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at TEXT NOT NULL,
            scraper_type TEXT NOT NULL,
            url TEXT NOT NULL,
            page_count INTEGER NOT NULL,
            item_count INTEGER NOT NULL,
            duration_seconds REAL NOT NULL,
            status TEXT NOT NULL,
            error_message TEXT
        )
        """
    )

    vColumns = vConnection.execute(
        """
        PRAGMA table_info(history)
        """
    ).fetchall()

    vColumnNames = [
        vColumn[1]
        for vColumn in vColumns
    ]

    if "error_message" not in vColumnNames:
        vConnection.execute(
            """
            ALTER TABLE history
            ADD COLUMN error_message TEXT
            """
        )

    vConnection.commit()
    vConnection.close()


def save_history(pDatabasePath, pEntry):
    """
    Enregistre une entrée dans l'historique.

    :param pDatabasePath: Chemin vers la base SQLite.
    :param pEntry: Entrée d'historique à enregistrer.
    """

    vConnection = connect_database(
        pDatabasePath
    )

    vConnection.execute(
        """
        INSERT INTO history (
            started_at,
            scraper_type,
            url,
            page_count,
            item_count,
            duration_seconds,
            status,
            error_message
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            pEntry.started_at.isoformat(),
            pEntry.scraper_type,
            pEntry.url,
            pEntry.page_count,
            pEntry.item_count,
            pEntry.duration_seconds,
            pEntry.status,
            pEntry.error_message
        )
    )

    vConnection.commit()
    vConnection.close()


def get_history(pDatabasePath):
    """
    Récupère les entrées de l'historique.

    :param pDatabasePath: Chemin vers la base SQLite.
    :return: Liste des entrées d'historique.
    """

    initialize_history(
        pDatabasePath
    )

    vConnection = connect_database(
        pDatabasePath
    )

    vRows = vConnection.execute(
        """
        SELECT
            started_at,
            scraper_type,
            url,
            page_count,
            item_count,
            duration_seconds,
            status,
            error_message
        FROM history
        ORDER BY started_at DESC
        """
    ).fetchall()

    vConnection.close()

    vEntries = []

    for vRow in vRows:
        vEntry = HistoryEntry(
            started_at=datetime.fromisoformat(vRow[0]),
            scraper_type=vRow[1],
            url=vRow[2],
            page_count=vRow[3],
            item_count=vRow[4],
            duration_seconds=vRow[5],
            status=vRow[6],
            error_message=vRow[7]
        )

        vEntries.append(
            vEntry
        )

    rEntries = vEntries
    return rEntries