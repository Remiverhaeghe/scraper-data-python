# ============================================================================
# Tests du modèle représentant l'historique des scrapers
# ============================================================================


from datetime import datetime

from scraper.history import HistoryEntry


def test_history_entry_contains_scraping_information():
    """
    Vérifie qu'une entrée d'historique contient les informations du scraping.
    """

    vStartedAt = datetime(2026, 9, 21, 17, 42, 10)

    vEntry = HistoryEntry(
        started_at=vStartedAt,
        scraper_type="book",
        url="https://example.com/books",
        page_count=5,
        item_count=100,
        duration_seconds=4.82,
        status="success"
    )

    assert vEntry.started_at == vStartedAt
    assert vEntry.scraper_type == "book"
    assert vEntry.url == "https://example.com/books"
    assert vEntry.page_count == 5
    assert vEntry.item_count == 100
    assert vEntry.duration_seconds == 4.82
    assert vEntry.status == "success"
    assert vEntry.error_message is None


def test_history_entry_contains_error_message():
    """
    Vérifie qu'une entrée d'historique peut contenir une erreur.
    """

    vEntry = HistoryEntry(
        started_at=datetime(2026, 9, 21, 18, 10, 15),
        scraper_type="job",
        url="https://example.com/jobs",
        page_count=2,
        item_count=10,
        duration_seconds=1.25,
        status="error",
        error_message="Erreur de récupération."
    )

    assert vEntry.status == "error"
    assert vEntry.error_message == "Erreur de récupération."