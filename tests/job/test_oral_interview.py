"""Tests de l'entretien oral simulé : questions, notes, durée, séances et téléphone"""

import random
from datetime import datetime

import pytest

from job.oral_interview import (
    SESSION_LENGTH,
    answer_oral,
    build_oral_view,
    build_questions,
    rate_duration,
    record_phone_session,
    start_oral,
    stop_oral,
)
from job.progress import load_activity
from storage.database import initialize_database

NOW = datetime(2026, 10, 31, 9, 0)


@pytest.fixture
def database_file(tmp_path):
    """Fournit une base vide."""

    rDatabaseFile = tmp_path / "scraper.db"
    initialize_database(rDatabaseFile)

    return rDatabaseFile


@pytest.mark.parametrize(
    "pSeconds, pExpected", [(5, 0), (19.9, 0), (20, 2), (90, 2), (91, 1)]
)
def test_duration_is_rated_from_the_measured_time(pSeconds, pExpected):
    """Vérifie la note de durée : trop courte, dans le temps, au-delà."""

    assert rate_duration(pSeconds, 90) == pExpected


def test_each_mode_has_questions_with_a_hint(database_file):
    """Vérifie les questions classiques, pièges sans entretien prévu et techniques."""

    for vMode in ("general", "tricky", "technical"):
        vQuestions, vTarget = build_questions(database_file, vMode, NOW)

        assert len(vQuestions) >= SESSION_LENGTH and vTarget == ""
        assert all(vQuestion and vHint for vQuestion, vHint in vQuestions)


def test_session_is_answered_then_summed_up(database_file):
    """Vérifie une séance : choix refusés, question notée une fois, bilan, XP."""

    with pytest.raises(ValueError):
        start_oral(database_file, "inconnu", 90, NOW)

    with pytest.raises(ValueError):
        start_oral(database_file, "general", 45, NOW)

    with pytest.raises(ValueError, match="Aucune séance"):
        answer_oral(database_file, 0, 30, 2, 2, NOW)

    start_oral(database_file, "general", 60, NOW, random.Random(1))

    assert build_oral_view(database_file)["question"]["hint"]

    with pytest.raises(ValueError, match="Notez"):
        answer_oral(database_file, 0, 30, 3, 2, NOW)

    vFirst = answer_oral(database_file, 0, 10, 2, 1, NOW)

    assert (vFirst["score"], vFirst["duration_label"]) == (50, "trop courte")

    with pytest.raises(ValueError, match="déjà"):
        answer_oral(database_file, 0, 30, 2, 2, NOW)

    for vPosition in range(1, SESSION_LENGTH):
        vFeedback = answer_oral(database_file, vPosition, 45, 2, 2, NOW)

    vView = build_oral_view(database_file)

    assert vFeedback["finished"] and vView["session"] is None
    assert vView["last"]["score"] == 90
    assert vView["last"]["criteria"] == {
        "structure": 2.0,
        "example": 1.8,
        "duration": 1.6,
    }
    assert vView["weakest"] is None
    assert load_activity(database_file)[NOW.date()]["actions"]["oral_interview"] == 1


def test_weakest_criterion_and_stopped_session(database_file):
    """Vérifie le critère à travailler et une séance abandonnée sans être comptée."""

    record_phone_session(
        database_file,
        {
            "mode": "tricky",
            "duration": 90,
            "answers": [{"seconds": 40, "structure": 2, "example": 0}],
        },
        NOW,
    )
    start_oral(database_file, "technical", 120, NOW)
    stop_oral(database_file)

    vView = build_oral_view(database_file)

    assert vView["weakest"][0] == "Exemple concret"
    assert (vView["count"], vView["session"]) == (1, None)


@pytest.mark.parametrize(
    "pSession",
    [
        None,
        {"mode": "x", "duration": 90, "answers": [{}]},
        {"mode": "general", "duration": 90, "answers": []},
        {
            "mode": "general",
            "duration": 90,
            "answers": [{"seconds": "x", "structure": 1, "example": 1}],
        },
    ],
)
def test_unreadable_phone_sessions_are_refused(database_file, pSession):
    """Vérifie le refus d'une séance du téléphone illisible."""

    with pytest.raises(ValueError):
        record_phone_session(database_file, pSession, NOW)
