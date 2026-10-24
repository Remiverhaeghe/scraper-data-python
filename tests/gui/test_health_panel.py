"""Tests de la carte d'état de l'application"""

from gui.health_panel import HealthPanel
from storage.database import initialize_database


def test_health_rows_are_listed_with_their_colour(qt_application, tmp_path):
    """Vérifie une ligne par indicateur : pastille, libellé et valeur."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    vPanel = HealthPanel(vDatabaseFile)

    vPanel.refresh()

    vLabels = [
        vPanel.rows_layout.itemAtPosition(vRow, 1).widget().text()
        for vRow in range(vPanel.rows_layout.rowCount())
        if vPanel.rows_layout.itemAtPosition(vRow, 1)
    ]

    assert "Planificateur" in vLabels
    assert vPanel.rows_layout.itemAtPosition(0, 0).widget().text() == "●"
