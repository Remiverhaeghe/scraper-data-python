"""Tests du mode examen de la révision"""

import random
from datetime import datetime, timedelta

import pytest

from job.quiz import load_quiz
from job.quiz_exam import (
    EXAM_QUESTION_COUNT,
    answer_exam,
    describe_exam_results,
    describe_exam_summary,
    format_countdown,
    get_exam_question,
    get_remaining_seconds,
    load_exam,
    load_exam_results,
    start_exam,
    stop_exam,
    summarize_exam,
)
from storage.database import initialize_database
from storage.settings_repository import save_setting_values

NOW = datetime(2026, 10, 12, 10, 0)


@pytest.fixture
def database_file(tmp_path):
    """Crée une base vide."""

    rDatabaseFile = tmp_path / "scraper.db"

    initialize_database(rDatabaseFile)

    return rDatabaseFile


def test_exam_runs_from_start_to_summary(database_file):
    """Vérifie un examen complet : tirage, réponses justes et fausses, résultat."""

    vQuiz = load_quiz()
    # Les thèmes livrés sont tous informatiques : l'industrie n'a aucune question.
    with pytest.raises(ValueError, match="Aucune question"):
        start_exam(database_file, vQuiz, "Industrie", NOW)

    vExam = start_exam(database_file, vQuiz, "Informatique", NOW, random.Random(1))

    assert len(vExam["ids"]) == EXAM_QUESTION_COUNT

    for vIndex in range(EXAM_QUESTION_COUNT):
        vQuestion = get_exam_question(vQuiz, load_exam(database_file))

        assert vQuestion["position"] == vIndex + 1

        # Une réponse sur deux juste
        vChoice = vQuestion["answer"] if vIndex % 2 == 0 else 1 - vQuestion["answer"]
        vResult, vExam = answer_exam(
            database_file, vQuiz, vChoice, NOW + timedelta(minutes=vIndex + 1)
        )

        assert vResult["correct"] is (vIndex % 2 == 0)

    assert vExam["finished_at"]
    assert get_exam_question(vQuiz, vExam) is None

    vSummary = summarize_exam(vQuiz, vExam)

    assert (vSummary["correct"], vSummary["score"]) == (10, 50)
    assert (vSummary["minutes"], vSummary["overtime"]) == (20, False)
    assert sum(vCount for _, vCount in vSummary["to_review"]) == 10
    assert describe_exam_summary(vSummary).startswith("Note : 10 / 20 (50 %) en 20 min")

    with pytest.raises(ValueError, match="Aucun examen en cours"):
        answer_exam(database_file, vQuiz, 0, NOW)

    stop_exam(database_file)

    assert load_exam(database_file) is None


def test_exam_skips_deleted_question_and_reports_overtime(database_file):
    """Vérifie qu'une question disparue est passée et le dépassement de durée signalé."""

    vQuiz = load_quiz()
    start_exam(database_file, vQuiz, None, NOW, random.Random(2))

    vResult, vExam = answer_exam(database_file, {}, 0, NOW)

    assert vResult is None
    assert vExam["index"] == 1
    assert get_exam_question({}, vExam) is None

    vSummary = summarize_exam(
        vQuiz,
        {
            **vExam,
            "ids": vExam["ids"][:2],
            "finished_at": (NOW + timedelta(minutes=5)).isoformat(),
        },
    )

    assert vSummary["overtime"] is True
    assert "au-delà des 2 min conseillées" in describe_exam_summary(vSummary)
    assert describe_exam_summary({**vSummary, "to_review": []}).endswith(
        "Aucune erreur."
    )


def test_unreadable_exam_is_ignored(database_file, caplog):
    """Vérifie qu'un état d'examen illisible n'empêche pas la révision."""

    save_setting_values(database_file, {"quiz_exam": "{"})

    assert load_exam(database_file) is None
    assert "illisible" in caplog.text


def test_finished_exam_is_kept_with_its_offer(database_file):
    """Vérifie la note gardée pour l'offre et le compte à rebours."""

    vQuiz = load_quiz()
    vExam = start_exam(
        database_file,
        vQuiz,
        "Informatique",
        NOW,
        random.Random(2),
        pTitle="Entretien : Dev",
        pOfferKey=("remotive", "7"),
    )

    assert get_remaining_seconds(vExam, NOW + timedelta(minutes=5)) == 15 * 60
    assert format_countdown(15 * 60 + 5) == "Temps restant : 15:05"
    assert format_countdown(-61) == "Temps dépassé de 01:01"

    for vIndex in range(EXAM_QUESTION_COUNT):
        vQuestion = get_exam_question(vQuiz, load_exam(database_file))
        answer_exam(
            database_file,
            vQuiz,
            vQuestion["answer"],
            NOW + timedelta(minutes=vIndex + 1),
        )

    vResults = load_exam_results(database_file, ("remotive", "7"))

    assert len(vResults) == 1
    assert (vResults[0]["score"], vResults[0]["seconds"]) == (100, 20 * 60)
    assert load_exam_results(database_file, ("remotive", "8")) == []
    assert describe_exam_results(vResults) == (
        "Examens blancs : meilleure note 100 %, dernière 100 % le 12/10/2026 "
        "(1 examen(s))."
    )
    assert describe_exam_results([]) == ""
