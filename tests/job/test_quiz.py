"""Tests de la révision technique et du contenu des questions"""

import json
import random
from datetime import datetime

import pandas as pd
import pytest

from job.quiz import (
    answer_question,
    build_quiz_overview,
    load_quiz,
    pick_question,
)
from storage.database import initialize_database
from storage.job_offers import save_offers
from storage.quiz_answers import get_last_answers

NOW = datetime(2026, 10, 11, 10, 0)


@pytest.fixture
def database_file(tmp_path):
    """Crée une base avec deux offres citant Java."""

    rDatabaseFile = tmp_path / "scraper.db"

    initialize_database(rDatabaseFile)
    save_offers(
        rDatabaseFile,
        pd.DataFrame(
            [
                {
                    "source": "remotive",
                    "source_id": vId,
                    "title": "Dev",
                    "skills": vSkills,
                }
                for vId, vSkills in (("1", ["Java", "SQL"]), ("2", ["Java"]))
            ]
        ),
        NOW,
    )

    return rDatabaseFile


def test_versioned_questions_are_valid():
    """Vérifie que chaque fichier de questions du dépôt se charge sans défaut."""

    vQuiz = load_quiz()

    assert {"java", "python", "sql", "javascript", "git", "practices"} <= set(vQuiz)
    assert all(len(vTheme["questions"]) >= 8 for vTheme in vQuiz.values())


def test_invalid_question_is_reported(tmp_path):
    """Vérifie le message d'une question dont la réponse n'existe pas."""

    (tmp_path / "theme.json").write_text(
        json.dumps(
            {
                "theme": "Test",
                "questions": [
                    {
                        "id": "q1",
                        "level": "débutant",
                        "question": "?",
                        "choices": ["a", "b"],
                        "answer": 2,
                        "explanation": "",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="theme.json, question q1 : réponse hors"):
        load_quiz(tmp_path)


def test_overview_suggests_themes_from_offers(database_file):
    """Vérifie l'ordre des thèmes selon les offres et le score après une réponse."""

    vQuiz = load_quiz()

    answer_question(database_file, vQuiz, "java-optional", 1, NOW)
    answer_question(database_file, vQuiz, "java-list-of", 0, NOW)

    vOverview = build_quiz_overview(database_file, vQuiz)

    assert [vTheme["label"] for vTheme in vOverview[:2]] == ["Java", "SQL"]
    assert vOverview[0]["offer_count"] == 2
    assert (vOverview[0]["answered"], vOverview[0]["to_review"]) == (2, 1)
    assert vOverview[0]["score"] == 10


def test_pick_question_modes_and_shuffle(database_file):
    """Vérifie les questions proposées selon le mode et le mélange des choix."""

    vQuiz = load_quiz()

    answer_question(database_file, vQuiz, "git-stash", 0, NOW)
    vAnswers = get_last_answers(database_file)

    vReview = pick_question(vQuiz, "git", "review", vAnswers, random.Random(1))

    assert vReview["id"] == "git-stash"
    assert sorted(vReview["shuffled"]) == list(enumerate(vReview["choices"]))

    for vSeed in range(10):
        vQuestion = pick_question(
            vQuiz, "git", "discover", vAnswers, random.Random(vSeed)
        )

        assert vQuestion["id"] != "git-stash"

    assert pick_question(vQuiz, "sql", "review", vAnswers) is None


def test_answer_question_rejects_unknown(database_file):
    """Vérifie le refus d'une question inconnue ou d'un choix hors liste."""

    vQuiz = load_quiz()

    vResult = answer_question(database_file, vQuiz, "sql-null", 1, NOW)

    assert vResult["correct"] is True
    assert vResult["answer"] == "Aucune ligne"

    for vQuestionId, vChoice in (("inconnue", 0), ("sql-null", 9)):
        with pytest.raises(ValueError):
            answer_question(database_file, vQuiz, vQuestionId, vChoice, NOW)
