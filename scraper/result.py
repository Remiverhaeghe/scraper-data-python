# ============================================================================
# Modèle commun représentant le résultat d'un scraping
# ============================================================================


from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class ScrapingResult:
    """
    Représente le résultat d'une opération de scraping.
    """

    items: list[Any]
    page_count: int
    duration_seconds: float
    started_at: datetime | None = None
    status: str = "success"
    error_message: str | None = None