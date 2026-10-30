"""Tests de la page des tests de recrutement"""

from gui.aptitude_page import AptitudePage
from job.aptitude import CATEGORIES, SESSION_SECONDS
from storage.aptitude_sessions import get_aptitude_sessions
from storage.database import initialize_database


def test_page_plays_a_perfect_session(qt_application, tmp_path):
    """Vérifie les tuiles, une partie sans faute enregistrée et son résultat."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    vPage = AptitudePage(vDatabaseFile)
    vPage.refresh()

    assert vPage.tiles_layout.count() == len(CATEGORIES)

    vPage.start_session("mecanique", 11)

    assert vPage.timer.isActive()

    for vQuestion in list(vPage.questions):
        vPage.choose(vQuestion["answer"])

    vSessions = get_aptitude_sessions(vDatabaseFile)

    assert not vPage.timer.isActive()
    assert [(vSession["category"], vSession["correct"]) for vSession in vSessions] == [
        ("mecanique", 10)
    ]
    assert vPage.result_label.text().startswith("Raisonnement mécanique : 10 / 10")
    assert vPage.cards["perfect"].value_label.text() == "0"

    vPage.show_choices()

    assert vPage.cards["perfect"].value_label.text() == "1"


def test_page_abandon_is_not_saved_and_timeout_finishes(
    qt_application, tmp_path, monkeypatch
):
    """Vérifie qu'un abandon n'est pas compté et qu'un temps écoulé termine la partie."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    vPage = AptitudePage(vDatabaseFile)

    vPage.start_session("plans", 3)
    vPage.choose(0)
    vPage.stop_session()

    assert not get_aptitude_sessions(vDatabaseFile)

    vPage.start_session("attention", 4)
    vPage.choose(vPage.questions[0]["answer"])
    monkeypatch.setattr(vPage, "get_elapsed", lambda: SESSION_SECONDS + 5)
    vPage.tick()

    vSessions = get_aptitude_sessions(vDatabaseFile)

    assert (vSessions[0]["correct"], vSessions[0]["duration_seconds"]) == (
        1,
        SESSION_SECONDS,
    )
    assert "9 sans réponse" in vPage.result_label.text()
