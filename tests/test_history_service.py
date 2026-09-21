# ============================================================================
# Tests du service de gestion de l'historique des scrapers
# ============================================================================


from datetime import datetime

from scraper.history_service import (
    build_history_entry,
    record_history
)
from scraper.result import ScrapingResult
from storage.history_repository import get_history


def test_build_history_entry_creates_entry_from_result():
    """
    Vérifie qu'un résultat de scraping est correctement transformé.
    """

    vStartedAt = datetime(2026, 9, 21, 17, 42, 10)

    vResult = ScrapingResult(
        items=["A", "B", "C"],
        page_count=2,
        duration_seconds=4.82,
        started_at=vStartedAt,
        status="success"
    )

    vEntry = build_history_entry(
        "book",
        "https://example.com/books",
        vResult
    )

    assert vEntry.started_at == vStartedAt
    assert vEntry.scraper_type == "book"
    assert vEntry.url == "https://example.com/books"
    assert vEntry.page_count == 2
    assert vEntry.item_count == 3
    assert vEntry.duration_seconds == 4.82
    assert vEntry.status == "success"
    assert vEntry.error_message is None


def test_build_history_entry_creates_error_entry():
    """
    Vérifie qu'une erreur est correctement transmise à l'historique.
    """

    vResult = ScrapingResult(
        items=["A"],
        page_count=2,
        duration_seconds=1.25,
        started_at=datetime(2026, 9, 21, 18, 10, 15),
        status="error",
        error_message="Erreur de récupération."
    )

    vEntry = build_history_entry(
        "job",
        "https://example.com/jobs",
        vResult
    )

    assert vEntry.status == "error"
    assert vEntry.error_message == "Erreur de récupération."


def test_record_history_saves_entry(tmp_path):
    """
    Vérifie qu'un résultat de scraping est enregistré dans SQLite.
    """

    vDatabasePath = tmp_path / "scraper.db"

    vResult = ScrapingResult(
        items=["A", "B"],
        page_count=1,
        duration_seconds=1.25,
        started_at=datetime(2026, 9, 21, 18, 10, 15),
        status="success"
    )

    vEntry = record_history(
        vDatabasePath,
        "job",
        "https://example.com/jobs",
        vResult
    )

    vEntries = get_history(
        vDatabasePath
    )

    assert len(vEntries) == 1
    assert vEntries[0] == vEntry


def test_record_history_saves_error_entry(tmp_path):
    """
    Vérifie qu'une erreur est enregistrée dans SQLite.
    """

    vDatabasePath = tmp_path / "scraper.db"

    vResult = ScrapingResult(
        items=["A"],
        page_count=2,
        duration_seconds=1.25,
        started_at=datetime(2026, 9, 21, 18, 10, 15),
        status="error",
        error_message="Erreur de récupération."
    )

    vEntry = record_history(
        vDatabasePath,
        "job",
        "https://example.com/jobs",
        vResult
    )

    vEntries = get_history(
        vDatabasePath
    )

    assert len(vEntries) == 1
    assert vEntries[0] == vEntry
    assert vEntries[0].status == "error"
    assert vEntries[0].error_message == (
        "Erreur de récupération."
    )