"""Service de gestion de l'historique des scrapers"""

from scraper.history import HistoryEntry
from scraper.result import ScrapingResult
from storage.history_repository import initialize_history, save_history


def build_history_entry(pScraperType, pUrl, pResult):
    """Construit une entrée d'historique à partir du résultat d'un scraping."""

    vEntry = HistoryEntry(
        started_at=pResult.started_at,
        scraper_type=pScraperType,
        url=pUrl,
        page_count=pResult.page_count,
        item_count=len(pResult.items),
        duration_seconds=pResult.duration_seconds,
        status=pResult.status,
        error_message=pResult.error_message,
    )

    rEntry = vEntry
    return rEntry


def record_history(pDatabasePath, pScraperType, pUrl, pResult):
    """Construit et enregistre une entrée d'historique."""

    initialize_history(pDatabasePath)

    vEntry = build_history_entry(pScraperType, pUrl, pResult)

    save_history(pDatabasePath, vEntry)

    rEntry = vEntry
    return rEntry
