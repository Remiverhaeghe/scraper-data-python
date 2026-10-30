"""Tests de la page Maven et Docker"""

from gui.devops_page import DevopsPage
from job.devops_levels import load_levels
from storage.database import initialize_database


def test_level_is_played_in_the_console(qt_application, tmp_path):
    """Vérifie l'erreur Maven affichée, puis la solution qui atteint l'objectif."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    vPage = DevopsPage(vDatabaseFile)
    vPage.refresh()

    assert len(vPage.tiles) == len(load_levels())

    vPage.open_level("maven-dependance")
    vPage.command_edit.setText("mvn package")
    vPage.run_command()

    assert (
        "package org.apache.commons.lang3 does not exist" in vPage.console.toPlainText()
    )

    vPage.show_solution()
    vPage.command_edit.setText("mvn package")
    vPage.run_command()

    assert "Objectif atteint · +20 XP" in vPage.status_label.text()
    assert vPage.passed_card.value_label.text() == f"1 / {len(load_levels())}"

    vPage.reset()

    assert not vPage.console.toPlainText()
