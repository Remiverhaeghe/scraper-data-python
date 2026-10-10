"""Gestion de la connexion et de l'initialisation de la base SQLite"""

import sqlite3
from pathlib import Path


def connect_database(pDatabasePath):
    """Ouvre une connexion vers la base SQLite."""

    vDatabasePath = Path(pDatabasePath)

    vDatabasePath.parent.mkdir(parents=True, exist_ok=True)

    vConnection = sqlite3.connect(vDatabasePath)

    rConnection = vConnection

    return rConnection


def initialize_database(pDatabasePath):
    """Initialise les tables nécessaires à l'application."""

    vConnection = connect_database(pDatabasePath)

    try:
        vConnection.execute("""
            CREATE TABLE IF NOT EXISTS job_tracking (
                source TEXT NOT NULL,
                source_id TEXT NOT NULL,
                first_seen_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                PRIMARY KEY (source, source_id)
            )
            """)

        vConnection.execute("""
            CREATE TABLE IF NOT EXISTS job_application (
                source TEXT NOT NULL,
                source_id TEXT NOT NULL,
                status TEXT NOT NULL,
                applied_at TEXT,
                follow_up_date TEXT,
                follow_up_count INTEGER NOT NULL DEFAULT 0,
                last_follow_up_at TEXT,
                notes TEXT,
                PRIMARY KEY (source, source_id),
                FOREIGN KEY (source, source_id)
                    REFERENCES job_tracking(source, source_id)
            )
            """)

        vConnection.commit()

    finally:
        vConnection.close()
