"""Tests de la page des pannes à résoudre"""

from gui.troubleshooting_page import TroubleshootingPage
from job.troubleshooting import load_results, load_scenarios
from storage.database import initialize_database


def test_page_solves_a_scenario_and_saves_it(qt_application, tmp_path):
    """Vérifie les tuiles, une mesure, une erreur, la réparation et l'enregistrement."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    vPage = TroubleshootingPage(vDatabaseFile)
    vPage.refresh()

    assert vPage.tiles_layout.count() == len(load_scenarios())

    vPage.start_scenario("verin-lent")
    vChecks = vPage.checks_layout.count()

    vPage.act("check:silencieux")

    assert vPage.checks_layout.count() == vChecks - 1
    assert "noirci" in vPage.log_layout.itemAt(0).widget().text()

    vPage.act("repair:joints")

    assert not load_results(vDatabaseFile)
    assert "pour rien : 1" in vPage.status_label.text()

    vPage.act("repair:silencieux")

    assert load_results(vDatabaseFile)[0]["scenario"] == "verin-lent"
    assert vPage.checks_layout.count() == 0
    assert "XP" in vPage.result_label.text()

    vPage.show_choices()

    assert vPage.cards["solved"].value_label.text() == f"1 / {len(load_scenarios())}"
