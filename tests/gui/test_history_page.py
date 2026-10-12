"""Tests de la page de l'historique"""

from datetime import datetime

from PySide6.QtWidgets import QLabel

from gui.history_page import HistoryPage, build_row
from gui.theme import COLORS
from gui.widgets import show_message
from job.presentation import UNKNOWN_SEARCH
from scraper.history import HistoryEntry
from storage.database import initialize_database
from storage.history_repository import save_history


def build_entry(**pValues):
    """Construit une exécution de recherche d'offres."""

    vValues = {
        "started_at": datetime(2026, 10, 9, 8, 30),
        "scraper_type": "job",
        "url": "multi-source",
        "page_count": 2,
        "item_count": 42,
        "duration_seconds": 3.25,
        "status": "partial",
        "error_message": "Jooble : délai dépassé",
        "parameters": {"keyword": "Java", "sources": ["adzuna", "jooble"]},
    }

    vValues.update(pValues)

    rEntry = HistoryEntry(**vValues)

    return rEntry


def test_build_row():
    """Vérifie les textes d'une ligne de l'historique."""

    assert build_row(build_entry()) == [
        "09/10/2026 08:30",
        "Java\nAdzuna, Jooble",
        "42",
        "3.2 s",
        "Partielle",
    ]


def test_build_row_for_books():
    """Vérifie qu'une exécution du domaine Livres reste lisible."""

    vRow = build_row(
        build_entry(scraper_type="book", url="https://example.com", parameters=None)
    )

    assert vRow[1] == "Livres · https://example.com"
    assert vRow[2] == "42"


def test_history_page_lists_executions(qt_application, tmp_path):
    """Vérifie l'affichage des exécutions et du détail d'erreur."""

    vDatabaseFile = tmp_path / "scraper.db"

    initialize_database(vDatabaseFile)
    save_history(vDatabaseFile, build_entry())

    vPage = HistoryPage(vDatabaseFile)
    vPage.refresh()

    assert vPage.table.rowCount() == 1
    assert vPage.table.item(0, 1).text() == "Java\nAdzuna, Jooble"
    assert vPage.table.item(0, 4).toolTip() == "Jooble : délai dépassé"
    assert vPage.message_label.text().startswith("1 dernière(s) exécution(s)")
    assert vPage.cards["executions"].value_label.text() == "1"
    assert vPage.cards["success_rate"].value_label.text() == "0 %"
    assert len(vPage.execution_chart.labels) == 1
    assert vPage.source_chart.shares == []


def test_build_row_without_parameters():
    """Vérifie qu'une exécution sans critères enregistrés le signale."""

    vRow = build_row(build_entry(parameters=None))

    assert vRow[1] == UNKNOWN_SEARCH


def test_information_message_drops_previous_colour(qt_application):
    """Vérifie qu'une information reprend le style de l'étiquette après une erreur."""

    vLabel = QLabel()

    show_message(vLabel, "Échec.", "danger")

    assert COLORS["danger"] in vLabel.styleSheet()

    show_message(vLabel, "3 exécution(s).", None)

    assert (vLabel.text(), vLabel.styleSheet()) == ("3 exécution(s).", "")
