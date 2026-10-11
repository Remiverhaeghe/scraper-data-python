"""Tests de la sauvegarde et de la réinitialisation de la base"""

import sqlite3
from datetime import datetime

import pandas as pd
import pytest

import storage.maintenance as maintenance
from job.schedule import load_schedule, save_notification_email
from storage.database import initialize_database
from storage.job_applications import save_application
from storage.job_offers import count_offers, save_offers
from storage.maintenance import backup_database, reset_database

NOW = datetime(2026, 10, 11, 9, 30, 15)


@pytest.fixture
def database_file(tmp_path):
    """Crée une base avec une offre, une candidature et un réglage."""

    rDatabaseFile = tmp_path / "scraper.db"

    initialize_database(rDatabaseFile)
    save_offers(
        rDatabaseFile,
        pd.DataFrame([{"source": "remotive", "source_id": "1", "title": "Offre"}]),
        NOW,
    )
    save_application(rDatabaseFile, "remotive", "1", "APPLIED")
    save_notification_email(rDatabaseFile, "moi@example.com")

    return rDatabaseFile


def count_rows(pDatabaseFile, pTable):
    """Compte les lignes d'une table."""

    vConnection = sqlite3.connect(pDatabaseFile)

    try:
        rCount = vConnection.execute(f"SELECT COUNT(*) FROM {pTable}").fetchone()[0]

    finally:
        vConnection.close()

    return rCount


def test_backup_database_copies_all_data(database_file):
    """Vérifie le nom horodaté et le contenu de la sauvegarde."""

    vBackupFile = backup_database(database_file, NOW)

    assert (
        vBackupFile == database_file.parent / "backups" / "scraper-20261011-093015.db"
    )
    assert count_rows(vBackupFile, "job_offer") == 1
    assert count_rows(vBackupFile, "job_application") == 1


def test_reset_database_empties_tables_and_keeps_schema(database_file):
    """Vérifie l'effacement des données, la sauvegarde et la base utilisable."""

    vBackupFile = reset_database(database_file, NOW)

    assert count_offers(database_file) == 0
    assert count_rows(database_file, "job_application") == 0
    assert load_schedule(database_file)["email"] is None
    assert count_rows(vBackupFile, "job_offer") == 1

    save_offers(
        database_file,
        pd.DataFrame([{"source": "remotive", "source_id": "2", "title": "Nouvelle"}]),
        NOW,
    )

    assert count_offers(database_file) == 1


def test_reset_database_keeps_data_when_backup_fails(database_file, monkeypatch):
    """Vérifie que rien n'est effacé si la sauvegarde échoue."""

    def refuse(pDatabaseFile, pNow):
        raise OSError("disque plein")

    monkeypatch.setattr(maintenance, "backup_database", refuse)

    with pytest.raises(OSError):
        reset_database(database_file, NOW)

    assert count_offers(database_file) == 1
