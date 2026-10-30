"""Tests de la page du simulateur d'automate"""

from gui.ladder_page import LadderPage
from job.ladder_game import load_ladder_progress, load_levels
from storage.database import initialize_database


def test_level_is_checked_and_simulated(qt_application, tmp_path):
    """Vérifie l'erreur affichée, la réussite enregistrée et la simulation pilotée."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    vPage = LadderPage(vDatabaseFile)
    vPage.refresh()

    assert vPage.tiles_layout.count() == len(load_levels())

    vLevel = load_levels()["marche-arret"]
    vPage.open_level("marche-arret", "moteur = !(marche)")

    assert "parenthèse" in vPage.error_label.text()

    vPage.show_solution()
    vPage.check_program()

    assert "Niveau réussi · +25 XP" in vPage.results_label.text()
    assert load_ladder_progress(vDatabaseFile)["marche-arret"]["program"] == (
        vLevel["solution"]
    )
    assert vPage.passed_card.value_label.text() == f"1 / {len(load_levels())}"

    vPage.toggle_simulation()
    vPage.input_buttons["marche"].setDown(True)
    vPage.step()
    vPage.input_buttons["marche"].setDown(False)

    for _ in range(3):
        vPage.step()

    assert vPage.simulator.values["moteur"]

    vPage.input_buttons["arret"].setDown(True)
    vPage.step()

    assert not vPage.simulator.values["moteur"]

    vPage.show_choices()

    assert not vPage.timer.isActive()


def test_held_buttons_drive_the_two_hand_press(qt_application, tmp_path):
    """Vérifie les boutons maintenus de la commande bimanuelle et la presse qui sort."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    vPage = LadderPage(vDatabaseFile)
    vPage.open_level("bimanuelle", load_levels()["bimanuelle"]["solution"])

    assert vPage.input_buttons["gauche"].isCheckable()
    assert vPage.input_buttons["gauche"].text() == "gauche"

    vPage.toggle_simulation()
    vPage.input_buttons["gauche"].setChecked(True)
    vPage.input_buttons["droite"].setChecked(True)

    for _ in range(3):
        vPage.step()

    assert vPage.simulator.values["sortir"]
    assert vPage.machine_view.is_motor_running() is False

    vPage.show_choices()
