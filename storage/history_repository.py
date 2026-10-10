"""Persistance des entrées d'historique dans SQLite"""

import json
from datetime import datetime

from scraper.history import HistoryEntry
from storage.database import connect_database


def save_history(pDatabasePath, pEntry):
    """Enregistre une entrée dans l'historique."""

    vConnection = connect_database(pDatabasePath)

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
            error_message,
            parameters
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            pEntry.started_at.isoformat(),
            pEntry.scraper_type,
            pEntry.url,
            pEntry.page_count,
            pEntry.item_count,
            pEntry.duration_seconds,
            pEntry.status,
            pEntry.error_message,
            (
                json.dumps(pEntry.parameters, ensure_ascii=False)
                if pEntry.parameters is not None
                else None
            ),
        ),
    )

    vConnection.commit()
    vConnection.close()


def get_history(pDatabasePath, pLimit=None):
    """Récupère les entrées de l'historique, des plus récentes aux plus anciennes."""

    vQuery = """
        SELECT
            started_at,
            scraper_type,
            url,
            page_count,
            item_count,
            duration_seconds,
            status,
            error_message,
            parameters
        FROM history
        ORDER BY started_at DESC
        """

    vParams = []

    if pLimit is not None:
        vQuery += " LIMIT ?"
        vParams.append(pLimit)

    vConnection = connect_database(pDatabasePath)

    vRows = vConnection.execute(vQuery, vParams).fetchall()

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
            error_message=vRow[7],
            parameters=json.loads(vRow[8]) if vRow[8] else None,
        )

        vEntries.append(vEntry)

    rEntries = vEntries
    return rEntries
