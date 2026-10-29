"""Tests de la page Mon marché"""

import json

import gui.market_page as market_page
import job.labour_market as labour_market
from gui.market_page import MarketPage
from storage.database import initialize_database


def test_market_page_fills_cards_and_tables(qt_application, tmp_path):
    """Vérifie l'affichage d'une base vide : zéro offre, salaire visé à régler."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)

    vPage = MarketPage(vDatabaseFile)
    vPage.refresh()

    assert vPage.cards["offer_count"].value_label.text() == "0"
    assert vPage.cards["target"].value_label.text() == "À régler"
    assert vPage.skills_table.rowCount() == 0
    assert vPage.skills_table.columnCount() == 6


def test_exam_button_sends_the_priority_skills(qt_application, tmp_path):
    """Vérifie le bouton d'examen : désactivé sans priorité, puis les compétences émises."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    vPage = MarketPage(vDatabaseFile)
    vRequested = []
    vPage.exam_requested.connect(vRequested.append)
    vPage.refresh()

    assert not vPage.exam_button.isEnabled()

    vPage.priority_skills = ["Python", "SQL"]
    vPage.exam_button.setEnabled(True)
    vPage.exam_button.click()

    assert vRequested == [["Python", "SQL"]]


def test_outlook_is_downloaded_then_shown_by_zone(
    qt_application, tmp_path, monkeypatch
):
    """Vérifie l'enquête absente, son téléchargement, puis les listes par zone."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    monkeypatch.setattr(labour_market, "BMO_DIRECTORY", tmp_path / "bmo")
    vPage = MarketPage(vDatabaseFile)
    vPage.refresh()

    assert vPage.outlook_label.text().startswith("Téléchargez l'enquête")
    assert vPage.zone_combo.isHidden()

    def download(**_pOptions):
        (tmp_path / "bmo").mkdir()
        (tmp_path / "bmo" / "bmo-2026.json").write_text(
            json.dumps(
                {
                    "year": 2026,
                    "jobs": {
                        "J1X80": {
                            "label": "Développeurs",
                            "family": "Informatique",
                            "france": [900, 500, 0],
                            "departments": {"59": [100, 60, 0]},
                        }
                    },
                    "departments": {"59": "Nord"},
                }
            ),
            encoding="utf-8",
        )

    monkeypatch.setattr(market_page, "refresh_labour_market", download)
    vPage.run_outlook_download()
    qt_application.processEvents()

    assert vPage.outlook_label.text() == "Enquête 2026 · France"
    assert "Développeurs" in vPage.outlook_lists["top"][1].text()

    vPage.zone_combo.setCurrentIndex(vPage.zone_combo.findData("59"))
    vPage.show_outlook()

    assert vPage.outlook_label.text() == "Enquête 2026 · Nord"

    def fail(**_pOptions):
        raise OSError("hors ligne")

    monkeypatch.setattr(market_page, "refresh_labour_market", fail)
    vPage.run_outlook_download()
    qt_application.processEvents()

    assert vPage.outlook_label.text().startswith("Téléchargement impossible")
