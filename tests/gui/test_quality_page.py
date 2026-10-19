"""Tests de la page de qualité des données"""

from datetime import datetime

import pandas as pd

import gui.offer_purge_panel as offer_purge_panel
import gui.quality_page as quality_page
from gui.quality_page import QualityPage
from storage.database import initialize_database
from storage.job_offers import count_offers, save_offers


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

    assert vPage.table.rowCount() == 2
    assert vPage.table.item(0, 0).text() == "Remotive"
    assert vPage.table.item(0, 3).text() == "100 %"
    assert vPage.table.item(1, 0).text() == "Toutes sources"
    assert vPage.statistic_cards["count"].value_label.text() == "1"
    assert vPage.statistic_cards["best"].label.text().endswith(": Remotive")
    assert vPage.export_button.text() == "Exporter les offres à vérifier (1)"
    assert vPage.problems_label.text().startswith("1 offre(s) à vérifier")

    monkeypatch.setattr(
        quality_page.QFileDialog,
        "getSaveFileName",
        lambda *pArgs: (str(vExportFile), ""),
    )
    vPage.export_problems()

    assert "titre en plusieurs segments" in vExportFile.read_text(encoding="utf-8")


def test_off_topic_offers_are_purged_after_preview(
    qt_application, tmp_path, monkeypatch
):
    """Vérifie l'aperçu, son invalidation par la saisie et la suppression confirmée."""

    vDatabaseFile = tmp_path / "scraper.db"

    initialize_database(vDatabaseFile)
    save_offers(
        vDatabaseFile,
        pd.DataFrame(
            [
                {"source": "remotive", "source_id": "1", "title": "Stage Java"},
                {"source": "remotive", "source_id": "2", "title": "Développeur"},
            ]
        ),
        datetime(2026, 10, 11),
    )

    vPage = QualityPage(vDatabaseFile)
    vPage.refresh()
    vPanel = vPage.purge_panel

    vPanel.words_edit.setText("stage")
    vPanel.preview()

    assert vPanel.preview_list.count() == 1
    assert vPanel.delete_button.text() == "Supprimer 1 offre(s)"

    vPanel.words_edit.setText("stage, alternance")

    assert not vPanel.delete_button.isEnabled()

    vPanel.preview()
    monkeypatch.setattr(
        offer_purge_panel.QMessageBox,
        "question",
        lambda *_: offer_purge_panel.QMessageBox.StandardButton.Yes,
    )
    vPanel.delete()

    assert count_offers(vDatabaseFile) == 1
    assert vPanel.message_label.text().startswith("1 offre(s) supprimée(s)")
    assert vPage.statistic_cards["count"].value_label.text() == "1"
