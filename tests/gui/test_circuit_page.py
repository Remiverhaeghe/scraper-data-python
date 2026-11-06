"""Tests de la page des schémas électriques"""

import pytest

from gui import circuit_page
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


TRIPPING_SCHEMA = {
    "components": [
        {"id": "alimentation", "type": "alimentation", "x": 0, "y": 0},
        {"id": "disjoncteur", "type": "disjoncteur", "x": 1, "y": 0},
    ],
    "wires": [
        ["alimentation", "L", "disjoncteur", "1"],
        ["disjoncteur", "2", "alimentation", "N"],
    ],
}


@pytest.fixture(name="free_page")
def fixture_free_page(qt_application, tmp_path):
    """Ouvre le mode libre sur une base neuve."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    rPage = CircuitPage(vDatabaseFile)
    rPage.refresh()
    rPage.open_free()

    return rPage


def test_unreadable_progress_is_reported(qt_application, tmp_path, monkeypatch):
    """Vérifie le message affiché quand la progression ne peut pas être lue."""

    def fail(_pDatabaseFile):
        raise OSError("base verrouillée")

    monkeypatch.setattr(circuit_page, "build_circuit_overview", fail)
    vPage = CircuitPage(tmp_path / "scraper.db")
    vPage.refresh()

    assert vPage.message_label.text() == "La progression n'a pas pu être lue."


def test_unsaved_attempt_still_shows_the_result(qt_application, tmp_path, monkeypatch):
    """Vérifie qu'un essai non enregistré affiche la réussite, sans gain d'XP."""

    def fail(*_pArgs):
        raise OSError("disque plein")

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    monkeypatch.setattr(circuit_page, "save_attempt", fail)
    vPage = CircuitPage(vDatabaseFile)
    vPage.open_level("demarrage-moteur")
    vPage.show_solution()
    vPage.check_level()

    assert vPage.results_label.text().startswith("<h3>Montage réussi</h3>")


def test_tripped_breaker_is_rearmed_by_closing_it(free_page):
    """Vérifie qu'un disjoncteur déclenché se réarme en le refermant, puis redéclenche."""

    free_page.start_simulation()
    free_page.operate("disjoncteur", True)

    assert free_page.circuit is None

    free_page.editor.load_answer(TRIPPING_SCHEMA)
    free_page.start_simulation()
    free_page.step()

    assert free_page.memory["tripped"] == ["disjoncteur"]

    free_page.operate("disjoncteur", False)
    free_page.operate("disjoncteur", True)

    assert free_page.memory["tripped"] == ["disjoncteur"]
    assert free_page.faults_label.text()


def test_free_schema_errors_and_deletion(free_page, monkeypatch):
    """Vérifie un schéma vide, sans nom, non enregistré, puis supprimé."""

    def fail(*_pArgs):
        raise OSError("disque plein")

    free_page.save_free_schema()

    assert "Placez au moins un composant" in free_page.error_label.text()

    free_page.editor.load_answer(TRIPPING_SCHEMA)
    free_page.save_free_schema()

    assert free_page.error_label.text() == "Donnez un nom au schéma."

    free_page.name_edit.setText("Essai")
    free_page.save_free_schema()
    free_page.delete_free_schema()

    assert free_page.error_label.text() == "Schéma « Essai » supprimé."
    assert not build_circuit_overview(free_page.database_file)["schemas"]

    monkeypatch.setattr(circuit_page, "save_schema", fail)
    free_page.save_free_schema()

    assert free_page.error_label.text() == "Le schéma n'a pas pu être enregistré."

    free_page.delete_free_schema()
    free_page.show_choices()

    assert free_page.work_card.isHidden()


def test_export_svg(free_page, monkeypatch, tmp_path):
    """Vérifie l'export du dessin, l'annulation et l'échec d'écriture."""

    vTarget = tmp_path / "essai.svg"
    vChoices = [str(vTarget), "", str(tmp_path)]
    monkeypatch.setattr(
        circuit_page.QFileDialog,
        "getSaveFileName",
        lambda *_pArgs: (vChoices.pop(0), ""),
    )

    free_page.export_svg()

    assert len(vChoices) == 3

    free_page.editor.load_answer(TRIPPING_SCHEMA)
    free_page.name_edit.setText("Essai")
    free_page.export_svg()

    assert vTarget.read_text(encoding="utf-8").startswith("<svg")
    assert free_page.error_label.text() == f"Schéma exporté : {vTarget}"

    free_page.export_svg()

    assert not free_page.error_label.text()

    free_page.export_svg()

    assert free_page.error_label.text() == "Le fichier n'a pas pu être écrit."
