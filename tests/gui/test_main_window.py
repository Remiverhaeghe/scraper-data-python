"""Tests de la fenêtre principale"""

from PySide6.QtGui import QKeySequence, QShortcut

import gui.offer_assistant as offer_assistant
from gui.main_window import MainWindow
from job.presentation import FOLLOW_UP_FILTER
from job.quiz_exam import load_exam
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
    assert (
        vWindow.settings_page.data_panel.reset_message.text()
        == "Données réinitialisées."
    )


def test_offer_mock_exam_opens_quiz_page(qt_application, tmp_path, monkeypatch):
    """Vérifie que l'examen blanc d'une offre ouvre la révision sur l'examen."""

    vDatabaseFile = tmp_path / "scraper.db"

    initialize_database(vDatabaseFile)

    vWindow = MainWindow(vDatabaseFile, "Test")
    vPanel = vWindow.offers_page.detail_panel.assistant
    vPanel.offer = {
        "source": "adzuna",
        "source_id": "42",
        "title": "Développeur Python",
        "description": "API FastAPI et base PostgreSQL.",
    }
    monkeypatch.setattr(
        offer_assistant.QMessageBox,
        "question",
        lambda *pArgs: offer_assistant.QMessageBox.StandardButton.Yes,
    )

    vPanel.request_exam()

    assert vWindow.pages.currentWidget() is vWindow.quiz_page
    assert vWindow.quiz_page.mode == "exam"
    assert load_exam(vDatabaseFile)["title"] == "Entretien : Développeur Python"


def test_skills_page_opens_theme(qt_application, tmp_path):
    """Vérifie que « Réviser » sur une compétence ouvre la révision sur son thème."""

    vDatabaseFile = tmp_path / "scraper.db"

    initialize_database(vDatabaseFile)

    vWindow = MainWindow(vDatabaseFile, "Test")
    vWindow.skills_page.revise_requested.emit("sql")

    assert vWindow.pages.currentWidget() is vWindow.quiz_page
    assert vWindow.quiz_page.theme_key == "sql"


def test_applications_opens_its_page_and_preset_the_offers(qt_application, tmp_path):
    """Vérifie que la page Candidatures et le filtre des offres suivies sont distincts."""

    vDatabaseFile = tmp_path / "scraper.db"

    initialize_database(vDatabaseFile)

    vWindow = MainWindow(vDatabaseFile, "Test")

    vWindow.navigate("applications")

    assert vWindow.pages.currentWidget() is vWindow.applications_page

    vWindow.navigate("applied_offers")

    assert vWindow.pages.currentWidget() is vWindow.offers_page
    assert vWindow.offers_page.status_combo.currentData() == "APPLIED"


def test_menu_shows_pending_alerts(qt_application, tmp_path, monkeypatch):
    """Vérifie le nombre d'actions en attente à côté de « Candidatures »."""

    vDatabaseFile = tmp_path / "scraper.db"

    initialize_database(vDatabaseFile)
    monkeypatch.setattr(
        "gui.main_window.count_alerts",
        lambda pDatabaseFile, pNow: {"total": 2, "text": "2 relance(s) à faire"},
    )

    vWindow = MainWindow(vDatabaseFile, "Test")
    vWindow.navigate("settings")
    vItem = vWindow.navigation.item(vWindow.page_rows["applications"])

    assert vItem.text() == "Candidatures (2)"
    assert vItem.toolTip() == "2 relance(s) à faire"


def test_keyboard_shortcuts(qt_application, tmp_path):
    """Vérifie Ctrl+3 pour la troisième page, Ctrl+F et Échap sur les offres."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    vWindow = MainWindow(vDatabaseFile, "Test")
    vWindow.show()
    vShortcuts = {
        vShortcut.key().toString(): vShortcut
        for vShortcut in vWindow.findChildren(QShortcut)
    }

    vShortcuts["Ctrl+3"].activated.emit()

    assert vWindow.navigation.currentRow() == 2

    vShortcuts[QKeySequence(QKeySequence.StandardKey.Find).toString()].activated.emit()

    assert vWindow.pages.currentWidget() is vWindow.offers_page
    assert vWindow.focusWidget() is vWindow.offers_page.search_edit

    vWindow.offers_page.set_detail_visible(True)
    vShortcuts["Esc"].activated.emit()

    assert vWindow.offers_page.detail_panel.isHidden()

    vWindow.offers_page.toggle_detail()
    vWindow.close()
