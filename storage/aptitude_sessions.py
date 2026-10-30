"""Persistance des parties de tests de recrutement : catégorie, score et durée"""

import sqlite3

from storage.database import connect_database
from utils.logger import get_logger

logger = get_logger(__name__)


def add_aptitude_session(
    pDatabaseFile, pCategory, pCorrect, pTotal, pDurationSeconds, pPlayedAt
):
    """Enregistre une partie terminée ; retourne son identifiant."""

    vConnection = connect_database(pDatabaseFile)

    try:
        vCursor = vConnection.execute(
            """
            INSERT INTO aptitude_session (
                category, correct, total, duration_seconds, played_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                pCategory,
                pCorrect,
                pTotal,
                int(pDurationSeconds),
                pPlayedAt.isoformat(timespec="seconds"),
            ),
        )
        vConnection.commit()

        rSessionId = vCursor.lastrowid

    finally:
        vConnection.close()

    logger.info(
        "Test de recrutement %s : %s/%s en %s s",
        pCategory,
        pCorrect,
        pTotal,
        int(pDurationSeconds),
    )

    return rSessionId


def get_aptitude_sessions(pDatabaseFile):
    """Retourne toutes les parties, de la plus ancienne à la plus récente."""

    vConnection = connect_database(pDatabaseFile)

    try:
        vConnection.row_factory = sqlite3.Row

        vRows = vConnection.execute("""
            SELECT id, category, correct, total, duration_seconds, played_at
            FROM aptitude_session
            ORDER BY played_at, id
            """).fetchall()

    finally:
        vConnection.close()

    rSessions = [dict(vRow) for vRow in vRows]

    return rSessions
