"""Tests de la fenêtre principale"""

from gui.main_window import MainWindow
from job.presentation import FOLLOW_UP_FILTER
from job.schedule import load_schedule
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

    assert vWindow.status_bar.isHidden()

    vWindow.search_page.search_started.emit()

    assert vWindow.status_label.text() == "Recherche en cours"
    assert not vWindow.status_bar.isHidden()

    vWindow.search_page.search_ended.emit()

    assert vWindow.status_bar.isHidden()


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


def test_search_page_saves_scheduled_search(qt_application, tmp_path):
    """Vérifie que « Planifier cette recherche » enregistre critères et sources."""

    vDatabaseFile = tmp_path / "scraper.db"

    initialize_database(vDatabaseFile)

    vWindow = MainWindow(vDatabaseFile, "Test")
    vSearchPage = vWindow.search_page

    vSearchPage.keyword_edit.setText("Python")
    vSearchPage.request_schedule()

    vSearch = load_schedule(vDatabaseFile)["search"]

    assert vSearch["criteria"]["keyword"] == "Python"
    assert vSearch["sources"] == vSearchPage.get_selected_sources()
    assert vSearchPage.status_label.text() == "Recherche planifiée enregistrée"
    assert vWindow.settings_page.schedule_search_label.text().startswith("Python")


def test_reset_rebuilds_pages_with_message(qt_application, tmp_path):
    """Vérifie que les pages sont rechargées et le résultat affiché après reset."""

    vDatabaseFile = tmp_path / "scraper.db"

    initialize_database(vDatabaseFile)

    vWindow = MainWindow(vDatabaseFile, "Test")
    vOldSettingsPage = vWindow.settings_page

    vWindow.settings_page.data_reset.emit("Données réinitialisées.")

    assert vWindow.settings_page is not vOldSettingsPage
    assert vWindow.pages.currentWidget() is vWindow.settings_page
    assert vWindow.settings_page.reset_message.text() == "Données réinitialisées."
