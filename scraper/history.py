# ============================================================================
# Modèle représentant une entrée de l'historique des scrapers
# ============================================================================


from dataclasses import dataclass
from datetime import datetime


@dataclass
class HistoryEntry:
    """
    Représente une exécution enregistrée dans l'historique.
    """

    started_at: datetime
    scraper_type: str
    url: str
    page_count: int
    item_count: int
    duration_seconds: float
    status: str
    error_message: str | None = None