"""Tests de la page du bac à sable SQL"""

from gui.sql_page import SqlPage
from job.sql_levels import load_levels, load_sql_progress
from storage.database import initialize_database


def test_query_is_run_compared_and_saved(qt_application, tmp_path):
    """Vérifie l'erreur de dialecte, la réussite enregistrée et le dialecte changé."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    vPage = SqlPage(vDatabaseFile)
    vPage.refresh()

    assert len(vPage.tiles) == len(load_levels())

    vPage.open_level("plus-cheres", "SELECT TOP 3 id, cout FROM intervention")
    vPage.run_query()

    assert "pas TOP : ajoutez LIMIT 3" in vPage.verdict_label.text()
    assert vPage.expected_table.rowCount() == 3

    vPage.show_solution()
    vPage.run_query()

    assert "Niveau réussi · +15 XP" in vPage.verdict_label.text()
    assert vPage.result_table.item(0, 1).text() == "2340"
    assert vPage.passed_card.value_label.text() == f"1 / {len(load_levels())}"

    vPage.dialect_combo.setCurrentIndex(vPage.dialect_combo.findData("sqlserver"))

    assert load_sql_progress(vDatabaseFile)["dialect"] == "sqlserver"
    assert "TOP 3" in vPage.hint_label.text()
    assert not vPage.verdict_label.text()

    vPage.show_solution()

    assert vPage.editor.toPlainText().startswith("SELECT TOP 3")

    vPage.show_choices()

    assert vPage.choice_card.isVisibleTo(vPage)
