"""Tests des sessions de concentration : fenêtre comptée, bonus, bilan"""

from datetime import datetime, timedelta

import pytest

from job.focus_sessions import build_focus_view, finish_focus, start_focus
from job.progress import load_activity
from storage.database import initialize_database
from storage.quiz_answers import save_quiz_answer

START = datetime(2026, 10, 31, 9, 0)


@pytest.fixture
def database_file(tmp_path):
    """Fournit une base vide."""

    rDatabaseFile = tmp_path / "scraper.db"
    initialize_database(rDatabaseFile)

    return rDatabaseFile


def answer(pDatabaseFile, pMinutes, pCorrect=True):
    """Enregistre une réponse de révision pMinutes après le début de session."""

    save_quiz_answer(
        pDatabaseFile, "q1", "python", pCorrect, START + timedelta(minutes=pMinutes)
    )


def test_completed_session_doubles_the_points_made_during_it(database_file):
    """Vérifie le bonus d'une session menée à terme, sans compter l'avant ni l'après."""

    answer(database_file, -5)
    start_focus(database_file, "revise", START)
    answer(database_file, 3)
    answer(database_file, 10)
    answer(database_file, 12, pCorrect=False)
    answer(database_file, 30)

    vSummary = finish_focus(database_file, START + timedelta(minutes=40))

    assert vSummary["completed"] and vSummary["minutes"] == 25
    assert vSummary["actions"] == {"answer_right": 2, "answer_wrong": 1}
    assert vSummary["xp"] == vSummary["bonus"] == 2 * 5 + 2
    assert load_activity(database_file)[START.date()]["actions"]["focus_session"] == 1


def test_stopped_session_has_its_summary_without_bonus(database_file):
    """Vérifie une session arrêtée avant le terme : bilan, pas de bonus ni de points."""

    start_focus(database_file, "apply", START)
    answer(database_file, 2)

    vSummary = finish_focus(database_file, START + timedelta(minutes=10))

    assert (vSummary["completed"], vSummary["bonus"], vSummary["minutes"]) == (
        False,
        0,
        10,
    )
    assert "focus_session" not in load_activity(database_file)[START.date()]["actions"]
    assert finish_focus(database_file, START) is None


def test_view_closes_an_elapsed_session_and_refuses_bad_starts(database_file):
    """Vérifie le temps restant, la clôture d'une session échue et les refus."""

    with pytest.raises(ValueError):
        start_focus(database_file, "inconnu", START)

    start_focus(database_file, "interview", START)

    with pytest.raises(ValueError, match="déjà"):
        start_focus(database_file, "revise", START)

    assert (
        build_focus_view(database_file, START + timedelta(minutes=5))["current"][
            "remaining"
        ]
        == 20 * 60
    )

    vView = build_focus_view(database_file, START + timedelta(minutes=26))

    assert vView["current"] is None and vView["today"] == 1
    assert vView["last"]["goal_label"] == "Préparer un entretien"
