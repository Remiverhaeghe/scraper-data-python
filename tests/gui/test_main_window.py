"""Tests de la fenêtre principale"""

from gui.main_window import MainWindow
from job.presentation import FOLLOW_UP_FILTER
from storage.database import initialize_database


def test_navigation_to_follow_ups(qt_application, tmp_path):
    """Vérifie que l'accès aux relances ouvre les offres avec le bon filtre."""

    vDatabaseFile = tmp_path / "scraper.db"

    initialize_database(vDatabaseFile)

    vWindow = MainWindow(vDatabaseFile, "Test")

    vWindow.navigate("follow_ups")

    assert vWindow.pages.currentWidget() is vWindow.offers_page
    assert vWindow.offers_page.status_combo.currentData() == FOLLOW_UP_FILTER


def test_status_follows_search(qt_application, tmp_path):
    """Vérifie que l'état du menu latéral suit le début et la fin d'une recherche."""

    vDatabaseFile = tmp_path / "scraper.db"

    initialize_database(vDatabaseFile)

    vWindow = MainWindow(vDatabaseFile, "Test")

    vWindow.search_page.search_started.emit()

    assert vWindow.status_label.text() == "Recherche en cours"

    vWindow.search_page.search_ended.emit()

    assert vWindow.status_label.text() == "Prêt"


def test_rebuild_keeps_window_and_shows_page(qt_application, tmp_path):
    """Vérifie que le changement de thème repeint la même fenêtre."""

    vDatabaseFile = tmp_path / "scraper.db"

    initialize_database(vDatabaseFile)

    vWindow = MainWindow(vDatabaseFile, "Test")
    vOldPages = vWindow.pages

    vWindow.rebuild("settings")

    assert vWindow.pages is not vOldPages
    assert vWindow.pages.currentWidget() is vWindow.settings_page
    assert vWindow.windowTitle() == "Paramètres · Test"
