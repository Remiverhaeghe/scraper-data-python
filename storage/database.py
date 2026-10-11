"""Gestion de la connexion et des migrations de la base SQLite"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

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


def migrate_to_v2(pConnection):
    """Ajoute à l'historique les paramètres de chaque exécution."""

    # Paramètres au format JSON, absents pour les exécutions antérieures.
    pConnection.execute("ALTER TABLE history ADD COLUMN parameters TEXT")


def migrate_to_v3(pConnection):
    """Conserve chaque relance pour pouvoir les compter jour par jour."""

    pConnection.execute("""
        CREATE TABLE job_follow_up (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            source_id TEXT NOT NULL,
            followed_up_at TEXT NOT NULL,
            FOREIGN KEY (source, source_id)
                REFERENCES job_offer(source, source_id)
        )
        """)

    # Avant cette version, seule la dernière relance de chaque candidature est connue.
    pConnection.execute("""
        INSERT INTO job_follow_up (source, source_id, followed_up_at)
        SELECT source, source_id, last_follow_up_at
        FROM job_application
        WHERE last_follow_up_at IS NOT NULL
        """)


def migrate_to_v4(pConnection):
    """Ajoute les réglages modifiables depuis les interfaces."""

    pConnection.execute("""
        CREATE TABLE app_setting (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """)


def migrate_to_v5(pConnection):
    """Reprend les offres enregistrées avant deux corrections de parsing.

    Adzuna renvoyait parfois ses accents échappés (\\u00e9) ; Hacker News rangeait
    tout l'en-tête de l'annonce dans le lieu et le titre.
    """

    # Imports locaux : la reprise réutilise le parsing métier sans que le
    # stockage en dépende pour son fonctionnement courant.
    # pylint: disable=import-outside-toplevel
    from job.sources.hackernews.parser import parse_header
    from utils.helpers import decode_unicode_escapes

    vEscapedRows = pConnection.execute(r"""
        SELECT source, source_id, title, description
        FROM job_offer
        WHERE title LIKE '%\u%' OR description LIKE '%\u%'
        """).fetchall()

    pConnection.executemany(
        "UPDATE job_offer SET title = ?, description = ? "
        "WHERE source = ? AND source_id = ?",
        [
            (
                decode_unicode_escapes(vTitle),
                decode_unicode_escapes(vDescription),
                vSource,
                vSourceId,
            )
            for vSource, vSourceId, vTitle, vDescription in vEscapedRows
        ],
    )

    # L'ancien découpage conservait l'en-tête complet, entreprise en tête, dans le lieu.
    vHeaderRows = [
        (vSourceId, vLocation)
        for vSourceId, vCompany, vLocation in pConnection.execute("""
            SELECT source_id, company, location
            FROM job_offer
            WHERE source = 'hackernews' AND company IS NOT NULL
            """)
        if vLocation and vLocation.startswith(vCompany)
    ]

    vUpdates = []

    for vSourceId, vHeader in vHeaderRows:
        vDetails = parse_header(vHeader)
        vUpdates.append(
            (
                vDetails["title"],
                vDetails["location"],
                vDetails["employment"],
                vDetails["employment"],
                vDetails["salary"],
                vSourceId,
            )
        )

    pConnection.executemany(
        """
        UPDATE job_offer
        SET title = ?, location = ?, contract_type = ?, employment_type = ?,
            salary_label = ?
        WHERE source = 'hackernews' AND source_id = ?
        """,
        vUpdates,
    )

    logger.info(
        "Reprise des offres : %s texte(s) décodé(s), %s en-tête(s) Hacker News "
        "redécoupé(s)",
        len(vEscapedRows),
        len(vUpdates),
    )


def migrate_to_v6(pConnection):
    """Ajoute les recherches enregistrées, réutilisables depuis la page Recherche."""

    # Sources et critères sont stockés en JSON, comme dans l'historique.
    pConnection.execute("""
        CREATE TABLE saved_search (
            name TEXT PRIMARY KEY,
            sources TEXT NOT NULL,
            criteria TEXT NOT NULL,
            saved_at TEXT NOT NULL
        )
        """)


# Colonnes de date sur lesquelles un décompte quotidien est autorisé
DAILY_COUNT_COLUMNS = {
    ("job_offer", "first_seen_at"),
    ("job_application", "applied_at"),
    ("job_follow_up", "followed_up_at"),
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


MIGRATIONS = [
    migrate_to_v1,
    migrate_to_v2,
    migrate_to_v3,
    migrate_to_v4,
    migrate_to_v5,
    migrate_to_v6,
]


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
