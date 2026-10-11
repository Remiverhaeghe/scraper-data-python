"""Tests de la page de qualité des données"""

from datetime import datetime

import pandas as pd

import gui.quality_page as quality_page
from gui.quality_page import QualityPage
from storage.database import initialize_database
from storage.job_offers import save_offers


def test_quality_page_shows_rates_and_exports(qt_application, tmp_path, monkeypatch):
    """Vérifie le tableau par source et l'enregistrement de l'export."""

    vDatabaseFile = tmp_path / "scraper.db"
    vExportFile = tmp_path / "export.csv"

    initialize_database(vDatabaseFile)
    save_offers(
        vDatabaseFile,
        pd.DataFrame([{"source": "remotive", "source_id": "1", "title": "A | B"}]),
        datetime(2026, 10, 11),
    )

    vPage = QualityPage(vDatabaseFile)
    vPage.refresh()

    assert vPage.table.rowCount() == 1
    assert vPage.table.item(0, 0).text() == "Remotive"
    assert vPage.table.item(0, 2).text() == "100 %"

    monkeypatch.setattr(
        quality_page.QFileDialog,
        "getSaveFileName",
        lambda *pArgs: (str(vExportFile), ""),
    )
    vPage.export_problems()

    assert "titre en plusieurs segments" in vExportFile.read_text(encoding="utf-8")
