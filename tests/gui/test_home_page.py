"""Tests de la page d'accueil"""

from datetime import datetime

import pandas as pd

from gui.home_page import HomePage, describe_execution, load_statistics
from scraper.history import HistoryEntry
from storage.database import initialize_database
from storage.history_repository import save_history
from storage.job_applications import save_application
from storage.job_offers import save_offers


def build_database(pTmpPath):
    """Crée une base avec trois offres, une candidature et une exécution."""

    rDatabaseFile = pTmpPath / "scraper.db"

    initialize_database(rDatabaseFile)

    vItems = pd.DataFrame(
        [
            {"source": "lever", "source_id": vId, "title": f"Offre {vId}"}
            for vId in "123"
        ]
    )

    save_offers(rDatabaseFile, vItems.iloc[:2], datetime(2026, 9, 1))
    save_offers(rDatabaseFile, vItems.iloc[2:], datetime(2026, 10, 9))

    save_application(rDatabaseFile, "lever", "1", "APPLIED", pNow=datetime(2026, 10, 1))
    save_application(rDatabaseFile, "lever", "2", "IGNORED")

    save_history(
        rDatabaseFile,
        HistoryEntry(
            started_at=datetime(2026, 10, 9, 8, 30),
            scraper_type="job",
            url="multi-source",
            page_count=2,
            item_count=42,
            duration_seconds=3.25,
            status="partial",
        ),
    )

    return rDatabaseFile


def test_load_statistics(tmp_path):
    """Vérifie le calcul des indicateurs de l'accueil."""

    rStatistics = load_statistics(build_database(tmp_path), datetime(2026, 10, 10))

    assert rStatistics["offers"] == 2
    assert rStatistics["new_offers"] == 1
    assert rStatistics["applications"] == 1
    assert rStatistics["follow_ups"] == 1
    assert rStatistics["last_execution"].item_count == 42


def test_load_statistics_on_empty_database(tmp_path):
    """Vérifie que les indicateurs d'une base vide valent zéro."""

    vDatabaseFile = tmp_path / "scraper.db"

    initialize_database(vDatabaseFile)

    rStatistics = load_statistics(vDatabaseFile)

    assert rStatistics["offers"] == 0
    assert rStatistics["last_execution"] is None


def test_describe_execution():
    """Vérifie le résumé de la dernière exécution."""

    vEntry = HistoryEntry(
        started_at=datetime(2026, 10, 9, 8, 30),
        scraper_type="job",
        url="multi-source",
        page_count=2,
        item_count=42,
        duration_seconds=3.25,
        status="partial",
    )

    assert describe_execution(vEntry) == (
        "Dernière exécution le 09/10/2026 à 08:30 : 42 offre(s) en 3.2 s, partielle."
    )

    assert describe_execution(None) == "Aucune recherche lancée pour le moment."


def test_home_page_displays_statistics(qt_application, tmp_path):
    """Vérifie que la page affiche les indicateurs lus en base."""

    vPage = HomePage(build_database(tmp_path))

    vPage.refresh()

    assert vPage.cards["offers"].value_label.text() == "2"
    assert "42 offre(s)" in vPage.execution_label.text()
