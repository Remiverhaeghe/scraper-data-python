"""Tests du repository de l'historique"""

import sqlite3
from datetime import datetime

from scraper.history import HistoryEntry
from storage.database import initialize_database
from storage.history_repository import get_history, save_history


def test_save_history_stores_entry(tmp_path):
    """Vérifie qu'une entrée d'historique est correctement enregistrée."""

    vDatabasePath = tmp_path / "scraper.db"

    initialize_database(vDatabasePath)

    vEntry = HistoryEntry(
        started_at=datetime(2026, 9, 21, 17, 42, 10),
        scraper_type="book",
        url="https://example.com/books",
        page_count=5,
        item_count=100,
        duration_seconds=4.82,
        status="success",
    )

    save_history(vDatabasePath, vEntry)

    vConnection = sqlite3.connect(vDatabasePath)

    vRow = vConnection.execute("""
        SELECT
            started_at,
            scraper_type,
            url,
            page_count,
            item_count,
            duration_seconds,
            status,
            error_message
        FROM history
        """).fetchone()

    vConnection.close()

    assert vRow == (
        "2026-09-21T17:42:10",
        "book",
        "https://example.com/books",
        5,
        100,
        4.82,
        "success",
        None,
    )


def test_save_history_stores_error_message(tmp_path):
    """Vérifie qu'un message d'erreur est correctement enregistré."""

    vDatabasePath = tmp_path / "scraper.db"

    initialize_database(vDatabasePath)

    vEntry = HistoryEntry(
        started_at=datetime(2026, 9, 21, 18, 10, 15),
        scraper_type="job",
        url="https://example.com/jobs",
        page_count=2,
        item_count=10,
        duration_seconds=1.25,
        status="error",
        error_message="Erreur de récupération.",
    )

    save_history(vDatabasePath, vEntry)

    vEntries = get_history(vDatabasePath)

    assert len(vEntries) == 1
    assert vEntries[0].status == "error"
    assert vEntries[0].error_message == ("Erreur de récupération.")


def test_get_history_returns_entries_in_reverse_chronological_order(tmp_path):
    """Vérifie que l'historique est retourné du plus récent au plus ancien."""

    vDatabasePath = tmp_path / "scraper.db"

    initialize_database(vDatabasePath)

    vFirstEntry = HistoryEntry(
        started_at=datetime(2026, 9, 21, 17, 42, 10),
        scraper_type="book",
        url="https://example.com/books",
        page_count=5,
        item_count=100,
        duration_seconds=4.82,
        status="success",
    )

    vSecondEntry = HistoryEntry(
        started_at=datetime(2026, 9, 21, 18, 10, 15),
        scraper_type="job",
        url="https://example.com/jobs",
        page_count=3,
        item_count=42,
        duration_seconds=2.17,
        status="success",
    )

    save_history(vDatabasePath, vFirstEntry)

    save_history(vDatabasePath, vSecondEntry)

    vEntries = get_history(vDatabasePath)

    assert len(vEntries) == 2
    assert vEntries[0].started_at == vSecondEntry.started_at
    assert vEntries[1].started_at == vFirstEntry.started_at

    vLatestEntries = get_history(vDatabasePath, pLimit=1)

    assert [vEntry.started_at for vEntry in vLatestEntries] == [vSecondEntry.started_at]
