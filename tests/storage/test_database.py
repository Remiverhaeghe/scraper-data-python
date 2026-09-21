# ============================================================================
# Tests de la connexion à la base SQLite
# ============================================================================


import sqlite3

from storage.database import connect_database


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