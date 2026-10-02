# ============================================================================
# Gestion de la connexion et de l'initialisation de la base SQLite
# ============================================================================


import sqlite3
from pathlib import Path


def connect_database(pDatabasePath):
    """
    Ouvre une connexion vers la base SQLite.

    :param pDatabasePath: Chemin vers le fichier SQLite.
    :return: Connexion SQLite ouverte.
    """

    vDatabasePath = Path(
        pDatabasePath
    )

    vDatabasePath.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    vConnection = sqlite3.connect(
        vDatabasePath
    )

    rConnection = vConnection

    return rConnection


def initialize_database(pDatabasePath):
    """
    Initialise les tables nécessaires à l'application.

    :param pDatabasePath: Chemin vers la base SQLite.
    """

    vConnection = connect_database(
        pDatabasePath
    )

    try:
        vConnection.execute(
            """
            CREATE TABLE IF NOT EXISTS job_tracking (
                source TEXT NOT NULL,
                source_id TEXT NOT NULL,
                first_seen_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                PRIMARY KEY (source, source_id)
            )
            """
        )

        vConnection.commit()

    finally:
        vConnection.close()