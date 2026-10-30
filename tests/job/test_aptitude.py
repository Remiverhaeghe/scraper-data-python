"""Tests des tests de recrutement : questions générées, correction et scores"""

import random
from datetime import datetime

import pytest

from job.achievements import ACHIEVEMENTS, build_statistics
from job.aptitude import (
    CATEGORIES,
    QUESTIONS_PER_SESSION,
    build_aptitude_overview,
    create_mecanique_question,
    create_plans_question,
    finish_session,
    format_number,
    generate_session,
)
from job.progress import build_progress, load_activity
from storage.database import initialize_database

NOW = datetime(2026, 10, 30, 10, 0)


@pytest.mark.parametrize("pCategory", list(CATEGORIES))
def test_sessions_are_valid_and_reproducible(pCategory):
    """Vérifie 4 choix distincts, une réponse valide et la même partie pour une graine."""

    for vSeed in range(200):
        vQuestions = generate_session(pCategory, vSeed)

        assert len(vQuestions) == QUESTIONS_PER_SESSION

        for vQuestion in vQuestions:
            vChoices = vQuestion["choices"]

            assert len(vChoices) == 4 and 0 <= vQuestion["answer"] < 4
            assert (
                len(set(vChoices)) == 4
                or vChoices.count(vChoices[vQuestion["answer"]]) == 1
            )

    assert generate_session(pCategory, 5) == generate_session(pCategory, 5)
    assert generate_session(pCategory, 5) != generate_session(pCategory, 6)


def test_unknown_category_is_refused():
    """Vérifie le refus d'une catégorie inconnue."""

    with pytest.raises(ValueError):
        generate_session("astrologie", 1)


def test_mechanical_and_drawing_answers_are_right():
    """Vérifie les réponses par un calcul indépendant : engrenages et tolérances."""

    vRandom = random.Random(3)

    for _ in range(300):
        vQuestion = create_mecanique_question(vRandom)
        vRight = vQuestion["choices"][vQuestion["answer"]]

        if vQuestion["question"].endswith("tourne le dernier ?"):
            vCount = int(vQuestion["question"].split()[0])
            vFirst = (
                "antihoraire" if "antihoraire" in vQuestion["question"] else "horaire"
            )
            vExpected = (
                vFirst
                if vCount % 2
                else {"horaire": "antihoraire"}.get(vFirst, "horaire")
            )

            assert vRight == f"Sens {vExpected}"

        vDrawing = create_plans_question(vRandom)

        if "est-elle conforme" in vDrawing["question"]:
            vText = vDrawing["question"].replace(",", ".")
            vNominal = float(vText.split("Ø")[1].split(" ")[0])
            vTolerance = float(vText.split("±")[1].split(" ")[0])
            vMeasure = float(vText.split("mesurée à ")[1].split(" ")[0])
            vConform = abs(vMeasure - vNominal) <= vTolerance + 1e-9

            assert (vDrawing["choices"][vDrawing["answer"]] == "Conforme") == vConform


def test_finished_session_is_saved_and_rewarded(tmp_path):
    """Vérifie la correction, l'enregistrement, l'XP, la vue d'ensemble et le trophée."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    vQuestions = generate_session("calcul", 42)
    vAnswers = [vQuestion["answer"] for vQuestion in vQuestions]
    vAnswers[0] = (vAnswers[0] + 1) % 4
    vAnswers[1] = None

    vResult = finish_session(vDatabaseFile, "calcul", 42, vAnswers, 999, NOW)

    assert (vResult["correct"], vResult["score"], vResult["duration"]) == (8, 80, 150)
    assert vResult["xp"] == 26
    assert load_activity(vDatabaseFile)[NOW.date()]["xp"] == 26

    finish_session(
        vDatabaseFile,
        "calcul",
        7,
        [vQuestion["answer"] for vQuestion in generate_session("calcul", 7)],
        60,
        NOW,
    )
    vOverview = build_aptitude_overview(vDatabaseFile)
    vRow = next(vRow for vRow in vOverview["rows"] if vRow["category"] == "calcul")

    assert (vRow["sessions"], vRow["best"], vRow["last"], vRow["average"]) == (
        2,
        100,
        100,
        90,
    )
    assert vRow["ready"] and vOverview["weakest"] == "Calcul et proportions"
    assert vOverview["perfect"] == 1

    vProgress = build_progress(vDatabaseFile, NOW)
    vStatistics = build_statistics(
        vDatabaseFile, load_activity(vDatabaseFile), vProgress
    )

    assert (vStatistics["aptitude"], vStatistics["aptitude_perfect"]) == (2, 1)
    assert {"aptitude-first", "aptitude-perfect"} <= {
        vAchievement[0] for vAchievement in ACHIEVEMENTS
    }


def test_numbers_are_written_the_french_way():
    """Vérifie la virgule décimale et l'absence de zéro inutile."""

    assert [format_number(vValue) for vValue in (3, 2.5, 0.05, 20.1)] == [
        "3",
        "2,5",
        "0,05",
        "20,1",
    ]
