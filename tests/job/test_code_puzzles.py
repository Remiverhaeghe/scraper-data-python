"""Tests des puzzles de code : contenu, correction, séries, niveau et téléphone"""

import random
from datetime import datetime

import pytest

from job.achievements import build_statistics
from job.code_puzzles import (
    LEVELS,
    SERIES_LENGTH,
    TYPE_LABELS,
    answer_puzzle,
    build_puzzle_view,
    check_puzzle,
    draw_series,
    get_answer,
    get_next_level,
    grade_puzzle,
    load_puzzle_progress,
    load_puzzles,
    replay_series,
    start_series,
)
from job.progress import load_activity
from storage.database import initialize_database

NOW = datetime(2026, 10, 31, 9, 0)


def get_wrong_response(pPuzzle):
    """Retourne une réponse lisible mais fausse."""

    if pPuzzle["type"] == "ordre":
        return list(range(len(pPuzzle["items"])))[::-1]

    if pPuzzle["type"] == "saisie":
        return "?"

    rResponse = pPuzzle["line"] % len(pPuzzle["lines"])

    return rResponse


@pytest.fixture
def database_file(tmp_path):
    """Fournit une base vide."""

    rDatabaseFile = tmp_path / "scraper.db"
    initialize_database(rDatabaseFile)

    return rDatabaseFile


def test_delivered_puzzles_cover_each_type_and_level():
    """Vérifie que les puzzles livrés sont valides, avec cinq puzzles par type et niveau."""

    vPuzzles = load_puzzles().values()

    for vType in TYPE_LABELS:
        for vLevel in LEVELS:
            assert (
                sum(
                    vPuzzle["type"] == vType and vPuzzle["level"] == vLevel
                    for vPuzzle in vPuzzles
                )
                == 5
            )

    assert all(grade_puzzle(vPuzzle, get_answer(vPuzzle))[0] for vPuzzle in vPuzzles)


def test_invalid_puzzles_are_reported():
    """Vérifie les défauts d'un puzzle mal écrit."""

    vLine = {
        "id": "x",
        "type": "ligne",
        "language": "Python",
        "level": 1,
        "title": "T",
        "prompt": "P",
        "explanation": "E",
        "lines": ["a", "b", "c"],
        "line": 4,
    }

    assert check_puzzle(vLine).startswith("3 à 12 lignes")
    assert check_puzzle({**vLine, "line": 2}) == ""
    assert check_puzzle({**vLine, "level": 4}) == "type ou niveau inconnu"
    assert check_puzzle({"id": "x"}) == "champ manquant"


def test_wrong_line_is_graded_and_unreadable_answers_refused():
    """Vérifie la correction d'une ligne fautive, d'un trou et d'un ordre."""

    vPuzzles = load_puzzles()

    assert grade_puzzle(vPuzzles["python-moyenne"], 1) == (
        False,
        "ligne 2 : total = 0",
        "ligne 5 : return total / len(v)",
    )
    assert grade_puzzle(vPuzzles["sql-left-join"], " left  join ")[0] is False
    assert grade_puzzle(vPuzzles["sql-left-join"], "LEFT  OUTER JOIN")[0] is True

    for vPuzzleId, vResponse in (
        ("python-moyenne", 9),
        ("python-moyenne", True),
        ("sql-left-join", " "),
        ("python-lire-fichier", [0, 0, 1, 2, 3]),
    ):
        with pytest.raises(ValueError):
            grade_puzzle(vPuzzles[vPuzzleId], vResponse)


@pytest.mark.parametrize(
    "pLevel, pScore, pExpected",
    [(1, 8, 2), (3, 10, 3), (2, 5, 2), (2, 4, 1), (1, 0, 1)],
)
def test_level_follows_series_score(pLevel, pScore, pExpected):
    """Vérifie la montée après une bonne série et la descente après une mauvaise."""

    assert get_next_level(pLevel, pScore) == pExpected


def test_series_goes_from_easy_to_hard_and_prefers_new_puzzles():
    """Vérifie l'ordre croissant d'une série et le choix des puzzles jamais vus."""

    vPuzzles = load_puzzles()
    vSeen = {
        vId: {"right": 1, "wrong": 0, "last": True}
        for vId, vPuzzle in vPuzzles.items()
        if vPuzzle["level"] == 2
    }
    vSeries = draw_series(vPuzzles, 2, dict(list(vSeen.items())[:10]), random.Random(3))
    vLevels = [vPuzzles[vId]["level"] for vId in vSeries]

    assert len(set(vSeries)) == SERIES_LENGTH
    assert vLevels == sorted(vLevels) == [1, 1, 1, 2, 2, 2, 2, 2, 3, 3]
    assert not set(vSeries) & set(list(vSeen)[:10])


def test_series_is_answered_then_summed_up(database_file):
    """Vérifie une série jouée : série de réussites, niveau, bilan, XP et trophée."""

    start_series(database_file, random.Random(1))

    with pytest.raises(ValueError, match="déjà reçu"):
        answer_puzzle(database_file, 1, None, NOW)

    for vPosition in range(SERIES_LENGTH):
        vPuzzle = build_puzzle_view(database_file)["puzzle"]
        vResponse = (
            get_answer(vPuzzle) if vPosition >= 2 else get_wrong_response(vPuzzle)
        )
        vFeedback = answer_puzzle(database_file, vPosition, vResponse, NOW)

    vView = build_puzzle_view(database_file)
    vProgress = load_puzzle_progress(database_file)

    assert vFeedback["finished"] and vView["puzzle"] is None
    assert vView["recap"]["score"] == 8 and len(vView["recap"]["mistakes"]) == 2
    assert vProgress["streak"] == 8 and vProgress["best_streak"] == 8
    assert vProgress["level"] == 2
    assert load_activity(database_file)[NOW.date()]["actions"]["puzzle_series"] == 1
    assert (
        build_statistics(database_file, {}, {"best_streak": 0, "level": 1})[
            "puzzle_level"
        ]
        == 2
    )

    with pytest.raises(ValueError, match="Aucune série"):
        answer_puzzle(database_file, 0, 0, NOW)


def test_phone_series_is_graded_again(database_file):
    """Vérifie qu'une série du téléphone est recorrigée sans toucher la série en cours."""

    start_series(database_file, random.Random(2))
    vCurrent = load_puzzle_progress(database_file)["current"]
    vPuzzles = list(load_puzzles().values())[:SERIES_LENGTH]
    vAnswers = [
        {"id": vPuzzle["id"], "response": get_answer(vPuzzle)} for vPuzzle in vPuzzles
    ]
    vAnswers[0]["response"] = "illisible"

    assert replay_series(database_file, vAnswers, NOW) == SERIES_LENGTH - 1

    vProgress = load_puzzle_progress(database_file)

    assert vProgress["current"] == vCurrent
    assert vProgress["level"] == 2
    assert vProgress["history"][-1]["mistakes"][0]["given"] == "réponse illisible"

    for vBad in (vAnswers[:3], [vAnswers[0]] * SERIES_LENGTH, "x"):
        with pytest.raises(ValueError):
            replay_series(database_file, vBad, NOW)
