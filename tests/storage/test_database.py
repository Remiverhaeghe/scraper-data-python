"""Tests de la connexion et des migrations de la base SQLite"""

import sqlite3

import pytest

from storage.database import (
    MIGRATIONS,
    connect_database,
    get_schema_version,
    initialize_database,
    migrate_to_v1,
)


def get_table_names(pDatabaseFile):
    """Retourne le nom des tables présentes dans la base."""

    vConnection = connect_database(pDatabaseFile)

    try:
        vCursor = vConnection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )

        rTableNames = {vRow[0] for vRow in vCursor.fetchall()}

    finally:
        vConnection.close()

    return rTableNames


def test_connect_database_creates_database(tmp_path):
    """Vérifie qu'une base SQLite est correctement créée."""

    vDatabasePath = tmp_path / "scraper.db"

    vConnection = connect_database(vDatabasePath)

    assert vDatabasePath.exists()
    assert isinstance(vConnection, sqlite3.Connection)

    vConnection.close()


def test_initialize_database_creates_tables(tmp_path):
    """Vérifie que l'initialisation crée toutes les tables de l'application."""

    vDatabaseFile = tmp_path / "scraper.db"

    initialize_database(vDatabaseFile)

    vTableNames = get_table_names(vDatabaseFile)

    assert {"job_offer", "job_application", "history"} <= vTableNames
    assert "job_tracking" not in vTableNames


def test_initialize_database_sets_latest_version(tmp_path):
    """Vérifie que la base est à la dernière version après initialisation."""

    vDatabaseFile = tmp_path / "scraper.db"

    initialize_database(vDatabaseFile)

    vConnection = connect_database(vDatabaseFile)

    try:
        vVersion = get_schema_version(vConnection)

    finally:
        vConnection.close()

    assert vVersion == len(MIGRATIONS)


def test_initialize_database_can_run_twice(tmp_path):
    """Vérifie qu'une seconde initialisation ne rejoue pas les migrations."""

    vDatabaseFile = tmp_path / "scraper.db"

    initialize_database(vDatabaseFile)
    initialize_database(vDatabaseFile)

    assert "job_offer" in get_table_names(vDatabaseFile)


def test_failed_migration_keeps_previous_version(tmp_path):
    """Vérifie qu'une migration en échec ne laisse pas la base à moitié migrée."""

    vDatabaseFile = tmp_path / "scraper.db"

    vConnection = connect_database(vDatabaseFile)

    try:
        vConnection.execute("CREATE TABLE job_application (id INTEGER)")
        vConnection.commit()

    finally:
        vConnection.close()

    with pytest.raises(sqlite3.Error):
        initialize_database(vDatabaseFile)

    vConnection = connect_database(vDatabaseFile)

    try:
        vVersion = get_schema_version(vConnection)

    finally:
        vConnection.close()

    assert vVersion == 0
    assert "job_offer" not in get_table_names(vDatabaseFile)


def test_migration_to_v2_keeps_existing_history(tmp_path):
    """Vérifie qu'une base en version 1 passe en version 2 sans perdre de données."""

    vDatabaseFile = tmp_path / "scraper.db"

    vConnection = connect_database(vDatabaseFile)

    try:
        migrate_to_v1(vConnection)
        vConnection.execute("PRAGMA user_version = 1")
        vConnection.execute("""
            INSERT INTO history (
                started_at, scraper_type, url, page_count,
                item_count, duration_seconds, status
            )
            VALUES ('2026-10-01T08:00:00', 'job', 'multi-source', 2, 40, 3.5, 'success')
            """)
        vConnection.commit()

    finally:
        vConnection.close()

    initialize_database(vDatabaseFile)

    vConnection = connect_database(vDatabaseFile)

    try:
        vVersion = get_schema_version(vConnection)
        vRows = vConnection.execute(
            "SELECT item_count, parameters FROM history"
        ).fetchall()

    finally:
        vConnection.close()

    assert vVersion == 2
    assert vRows == [(40, None)]
