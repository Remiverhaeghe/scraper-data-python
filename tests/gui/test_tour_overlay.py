"""Tests de la visite guidée et des premiers pas de l'accueil"""

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QWidget

from gui.home_page import HomePage
from gui.main_window import MainWindow
from gui.tour_overlay import TourOverlay
from job.onboarding import TOUR_STEPS
from storage.database import initialize_database

# Méthode d'origine, avant que tests/gui/conftest.py ne la neutralise
MAYBE_START_TOUR = MainWindow.maybe_start_tour


def test_tour_opens_each_page_then_ends_at_home(qt_application):
    """Vérifie les pages ouvertes étape par étape, le retour en arrière et la fin."""

    vWindow = QWidget()
    vWindow.resize(1000, 700)
    vWindow.show()
    vPages = []
    vEnded = []
    vTour = TourOverlay(vWindow, vPages.append)
    vTour.finished.connect(lambda: vEnded.append(True))

    assert vTour.geometry() == vWindow.rect()
    assert not vTour.previous_button.isEnabled()

    for _ in range(len(TOUR_STEPS) - 1):
        vTour.next_step()

    assert vTour.next_button.text() == "Terminer"
    assert vTour.step_label.text() == f"Étape {len(TOUR_STEPS)} sur {len(TOUR_STEPS)}"

    vTour.show_step(vTour.index - 1)
    vWindow.resize(1200, 800)

    assert vTour.geometry() == vWindow.rect()

    vTour.show_step(len(TOUR_STEPS) - 1)
    vTour.next_step()

    assert vPages[: len(TOUR_STEPS)] == [vStep[0] for vStep in TOUR_STEPS]
    assert vPages[-1] == "home" and vEnded == [True]
    assert not vTour.grab().isNull()


def test_escape_skips_the_tour(qt_application):
    """Vérifie qu'Échap passe la visite."""

    vPages = []
    vWindow = QWidget()
    vTour = TourOverlay(vWindow, vPages.append)

    vTour.keyPressEvent(type("Key", (), {"key": lambda self: Qt.Key.Key_Escape})())

    assert vPages[-1] == "home"


def test_main_window_starts_the_tour_once(qt_application, tmp_path):
    """Vérifie la visite au premier lancement, puis plus jamais seule."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    QSettings().setValue("tour_done", False)
    vWindow = MainWindow(vDatabaseFile, "Test")

    MAYBE_START_TOUR(vWindow)

    assert vWindow.tour is not None
    assert QSettings().value("tour_done", False, bool)

    vWindow.tour.close_tour()
    MAYBE_START_TOUR(vWindow)

    assert vWindow.tour is None


def test_home_lists_start_quests_and_requests_the_tour(qt_application, tmp_path):
    """Vérifie les quêtes de démarrage de l'accueil et le bouton de la visite."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    vPage = HomePage(vDatabaseFile)
    vRequested = []
    vPage.tour_requested.connect(lambda: vRequested.append(True))
    vPage.refresh()

    assert not vPage.start_card.isHidden()
    assert vPage.start_layout.count() == 5

    vPage.tour_requested.emit()

    assert vRequested == [True]
