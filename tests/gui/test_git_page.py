"""Tests de la page du bac à sable Git"""

from gui.git_page import GitPage, format_level
from job.git_levels import LEVELS
from storage.database import initialize_database


def create_page(pDatabaseFile):
    """Crée la page Git sur une base vide."""

    initialize_database(pDatabaseFile)

    rPage = GitPage(pDatabaseFile)
    rPage.refresh()

    return rPage


def test_format_level():
    """Vérifie le libellé d'un niveau, réussi ou non."""

    vLevel = {"title": "Fusion", "series": "Bases", "par": 1, "best": None}

    assert format_level(vLevel) == "1 commande(s) attendue(s)"
    assert format_level({**vLevel, "best": 2}) == "Réussi en 2 commande(s), référence 1"


def test_level_is_played_undone_and_solved(qt_application, tmp_path):
    """Vérifie un niveau joué : erreur, annulation, aide, réussite et suite."""

    vPage = create_page(tmp_path / "scraper.db")

    assert len(vPage.level_buttons) == len(LEVELS)
    assert vPage.level_card.isHidden()

    vPage.open_level("premiers-commits")

    assert not vPage.level_card.isHidden()
    assert vPage.graph_widget.width() > 0

    vPage.command_edit.setText("git stash")
    vPage.run_command()

    assert vPage.message_label.text().startswith("Commande non prise en charge")
    assert vPage.command_edit.text() == "git stash"

    vPage.command_edit.setText("git commit")
    vPage.run_command()

    assert vPage.history == ["git commit"]
    assert vPage.command_edit.text() == ""

    vPage.undo()

    assert vPage.history == []

    vPage.show_hint()

    assert vPage.help_label.text().startswith("Indice :")

    vPage.show_solution()

    assert vPage.help_label.text() == "Solution : git commit · git commit"

    for _ in range(2):
        vPage.command_edit.setText("git commit")
        vPage.run_command()

    assert vPage.message_label.text().endswith("parcours optimal.")
    assert not vPage.command_edit.isEnabled()
    vTile = vPage.level_buttons["premiers-commits"]

    assert vTile.done
    assert vTile.isChecked()
    assert vTile.detail_label.text() == "Réussi en 2 commande(s), référence 2"
    assert not vPage.next_button.isHidden()

    vPage.open_next_level()

    assert vPage.level_id == "nouvelle-branche" and vPage.history == []

    vPage.command_edit.setText("git commit")
    vPage.run_command()
    vPage.restart()

    assert vPage.history == []


def test_server_graphs_follow_the_level(qt_application, tmp_path):
    """Vérifie que les graphes du serveur n'apparaissent que dans un niveau à origin."""

    vPage = create_page(tmp_path / "scraper.db")
    vPage.open_level("push")

    assert all(not vWidget.isHidden() for vWidget in vPage.server_parts)

    vPage.command_edit.setText("git push")
    vPage.run_command()

    assert vPage.message_label.text().endswith("parcours optimal.")

    vPage.open_level("premiers-commits")

    assert all(vWidget.isHidden() for vWidget in vPage.server_parts)
