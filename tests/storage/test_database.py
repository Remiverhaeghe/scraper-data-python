# ============================================================================
# Tests de la connexion à la base SQLite
# ============================================================================


import sqlite3

from storage.database import (
    connect_database,
    initialize_database
)


def test_connect_database_creates_database(tmp_path):
    """
    Vérifie qu'une base SQLite est correctement créée.
    """

    vDatabasePath = tmp_path / "scraper.db"

    vConnection = connect_database(
        vDatabasePath
    )

    assert vDatabasePath.exists()
    assert isinstance(
        vConnection,
        sqlite3.Connection
    )

    vConnection.close()

def test_initialize_database_creates_job_tracking_table(tmp_path):
    """
    Vérifie que l'initialisation crée la table de suivi des offres.
    """

    vDatabaseFile = tmp_path / "scraper.db"

    initialize_database(
        vDatabaseFile
    )

    vConnection = connect_database(
        vDatabaseFile
    )

    try:
        vCursor = vConnection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            AND name = 'job_tracking'
            """
        )

        vRow = vCursor.fetchone()

    finally:
        vConnection.close()

    assert vRow is not None

def test_initialize_database_creates_job_tracking_table(tmp_path):
    """
    Vérifie que l'initialisation crée la table de suivi des offres.
    """

    vDatabaseFile = tmp_path / "scraper.db"

    initialize_database(
        vDatabaseFile
    )

    vConnection = connect_database(
        vDatabaseFile
    )

    try:
        vCursor = vConnection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            AND name = 'job_tracking'
            """
        )

        vRow = vCursor.fetchone()

    finally:
        vConnection.close()

    assert vRow is not None