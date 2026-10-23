"""Tests de la page Mon marché"""

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
