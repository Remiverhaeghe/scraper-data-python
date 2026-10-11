"""Résultat générique d'une opération de scraping"""

from dataclasses import dataclass
from datetime import datetime

import pandas as pd


@dataclass
class ScrapingResult:
    """Contient le résultat et les informations d'une opération de scraping."""

    items: pd.DataFrame
    page_count: int
    duration_seconds: float
    started_at: datetime | None = None
    status: str = "success"
    error_message: str | None = None
    # Offres écartées faute de titre et de description, comptées par la qualité
    rejected_count: int = 0
