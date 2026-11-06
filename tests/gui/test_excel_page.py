"""Tests de la page de l'atelier Excel"""

from gui.excel_page import ExcelPage
from job.excel_levels import load_excel_progress, load_levels
from storage.database import initialize_database


def test_formula_is_filled_compared_and_saved(qt_application, tmp_path):
    """Vérifie le conseil sur un $ oublié, la réussite enregistrée et la feuille colorée."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    vPage = ExcelPage(vDatabaseFile)
    vPage.refresh()

    assert len(vPage.tiles) == len(load_levels())

    vPage.open_level("taux-fige", "=B2*(1+F1)")

    assert vPage.cell_label.text() == "C2"
    assert vPage.sheet_table.item(1, 2).text() == ""
    assert vPage.cells_table.isHidden()

    vPage.run_formula()

    assert "figez la ligne du taux" in vPage.verdict_label.text()
    assert vPage.cells_table.item(1, 1).text() == "14,90 €"

    vPage.show_solution()
    vPage.run_formula()

    assert "Niveau réussi · +15 XP" in vPage.verdict_label.text()
    assert vPage.sheet_table.item(1, 2).text() == "10,08 €"
    assert vPage.passed_card.value_label.text() == f"1 / {len(load_levels())}"
    assert load_excel_progress(vDatabaseFile)["levels"]["taux-fige"]["formula"] == (
        "=B2*(1+$F$1)"
    )

    vPage.editor.setText("=SUM(B2)")
    vPage.run_formula()

    assert "elle s&#x27;écrit SOMME" in vPage.verdict_label.text()

    vPage.show_choices()

    assert vPage.choice_card.isVisibleTo(vPage)
