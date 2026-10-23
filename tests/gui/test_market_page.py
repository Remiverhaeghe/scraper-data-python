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
