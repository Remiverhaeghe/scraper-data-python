"""Gestion de la connexion et des migrations de la base SQLite"""

import sqlite3
from pathlib import Path

from utils.logger import get_logger

logger = get_logger(__name__)


def connect_database(pDatabasePath):
    """Ouvre une connexion vers la base SQLite."""

    vDatabasePath = Path(pDatabasePath)

    vDatabasePath.parent.mkdir(parents=True, exist_ok=True)

    vConnection = sqlite3.connect(vDatabasePath)

    rConnection = vConnection

    return rConnection


def migrate_to_v1(pConnection):
    """Crée les tables des offres, des candidatures et de l'historique."""

    # Toute évolution de ce schéma passe par une nouvelle migration.
    pConnection.execute("""
        CREATE TABLE job_offer (
            source TEXT NOT NULL,
            source_id TEXT NOT NULL,
            first_seen_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL,
            title TEXT,
            company TEXT,
            company_id TEXT,
            url TEXT,
            location TEXT,
            city TEXT,
            postal_code TEXT,
            country TEXT,
            distance_km REAL,
            contract TEXT,
            contract_type TEXT,
            employment_type TEXT,
            salary_min REAL,
            salary_max REAL,
            salary_currency TEXT,
            salary_period TEXT,
            salary_label TEXT,
            salary_net_monthly_min REAL,
            salary_net_monthly_max REAL,
            salary_net_after_tax_monthly_min REAL,
            salary_net_after_tax_monthly_max REAL,
            has_13th_month INTEGER,
            has_bonus INTEGER,
            has_profit_sharing INTEGER,
            has_savings_plan INTEGER,
            remote TEXT,
            remote_days INTEGER,
            remote_type TEXT,
            nearest_metro TEXT,
            metro_distance_km REAL,
            date TEXT,
            published_at TEXT,
            updated_at TEXT,
            description TEXT,
            missions TEXT,
            requirements TEXT,
            education TEXT,
            skills TEXT,
            department TEXT,
            experience_level TEXT,
            job_type TEXT,
            PRIMARY KEY (source, source_id)
        )
        """)

    pConnection.execute("""
        CREATE TABLE job_application (
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
                REFERENCES job_offer(source, source_id)
        )
        """)

    pConnection.execute("""
        CREATE TABLE history (
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
        """)


MIGRATIONS = [migrate_to_v1]


def get_schema_version(pConnection):
    """Retourne la version du schéma enregistrée dans la base."""

    vCursor = pConnection.execute("PRAGMA user_version")

    rVersion = vCursor.fetchone()[0]

    return rVersion


def initialize_database(pDatabasePath):
    """Applique les migrations manquantes à la base."""

    vConnection = connect_database(pDatabasePath)

    try:
        vCurrentVersion = get_schema_version(vConnection)

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
