"""Tests de la page des schémas électriques"""

from gui.circuit_page import CircuitPage
from job.circuit_levels import build_circuit_overview, load_levels
from storage.database import initialize_database


def test_level_is_solved_then_operated(qt_application, tmp_path):
    """Vérifie la solution chargée, la réussite, puis le moteur piloté aux boutons."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    vPage = CircuitPage(vDatabaseFile)
    vPage.refresh()

    assert vPage.tiles_layout.count() == len(load_levels()) + 1

    vPage.open_level("demarrage-moteur")
    vPage.check_level()

    assert "Placez au moins un composant" in vPage.error_label.text()

    vPage.show_solution()
    vPage.check_level()

    assert "Montage réussi · +20 XP" in vPage.results_label.text()
    assert vPage.passed_card.value_label.text() == f"1 / {len(load_levels())}"

    vPage.start_simulation()
    vPage.control_buttons["bouton_marche"].pressed.emit()
    vPage.control_buttons["bouton_marche"].released.emit()

    assert vPage.memory["coils"]["bobine_relais"]
    assert vPage.control_buttons["bouton_marche"].text().endswith("ouvert")


def test_free_mode_saves_and_reopens_a_schema(qt_application, tmp_path):
    """Vérifie un schéma libre simulé, enregistré puis rouvert avec sa valeur."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    vPage = CircuitPage(vDatabaseFile)
    vPage.refresh()
    vPage.open_free()
    vPage.editor.load_answer(
        {
            "components": [
                {"id": "pile", "type": "pile", "x": 0, "y": 0},
                {"id": "lampe_bornes-1", "type": "lampe_bornes", "x": 1, "y": 0},
            ],
            "wires": [
                ["pile", "+", "lampe_bornes-1", "1"],
                ["lampe_bornes-1", "2", "pile", "−"],
            ],
        }
    )
    vPage.start_simulation()
    vPage.value_fields["pile"].setValue(12)
    vPage.name_edit.setText("Essai pile")
    vPage.save_free_schema()

    assert build_circuit_overview(vDatabaseFile)["schemas"] == ["Essai pile"]

    vPage.open_free("Essai pile")

    assert len(vPage.editor.get_answer()["wires"]) == 2
    assert vPage.free_values == {"pile": 12}
