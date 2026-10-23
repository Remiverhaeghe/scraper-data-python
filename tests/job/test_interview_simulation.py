"""Tests de la simulation d'entretien technique"""

import json
import random
from datetime import datetime

import pytest

from config import INTERVIEW_QUESTIONS_FILE
from job.interview_drill import build_deck
from job.interview_simulation import (
    ALL_THEMES,
    SIMULATION_SIZE,
    get_current_question,
    get_history,
    get_weak_questions,
    list_themes,
    load_interview_questions,
    load_simulation,
    record_answer,
    start_simulation,
    stop_simulation,
    summarize_simulation,
)
from storage.database import initialize_database

NOW = datetime(2026, 10, 23, 18)


@pytest.fixture(name="database_file")
def fixture_database_file(tmp_path):
    """Crée une base vide."""

    rDatabaseFile = tmp_path / "scraper.db"
    initialize_database(rDatabaseFile)

    return rDatabaseFile


def test_shipped_questions_are_valid():
    """Vérifie les questions livrées : champs, points clés et thèmes."""

    vQuestions = load_interview_questions()

    assert len(vQuestions) >= 15
    assert list_themes()[:2] == [ALL_THEMES, "Java"]
    assert {"Android", "Web", "Général"} <= set(list_themes())


def test_malformed_question_is_refused(tmp_path):
    """Vérifie le refus d'une question sans assez de points clés."""

    vFile = tmp_path / "questions.json"
    vData = json.loads(INTERVIEW_QUESTIONS_FILE.read_text(encoding="utf-8"))
    vData["questions"][0]["points"] = ["Un seul point"]
    vFile.write_text(json.dumps(vData), encoding="utf-8")

    with pytest.raises(ValueError, match="points clés"):
        load_interview_questions(vFile)


def test_simulation_from_start_to_summary(database_file):
    """Vérifie une série : tirage, notation, bilan, historique et cartes d'oral."""

    with pytest.raises(ValueError, match="Aucune question"):
        start_simulation(database_file, "Cobol", NOW)

    vSimulation = start_simulation(database_file, "Java", NOW, random.Random(1))

    assert len(vSimulation["ids"]) == SIMULATION_SIZE

    for vIndex in range(SIMULATION_SIZE):
        vQuestion = get_current_question(load_simulation(database_file))

        assert vQuestion["theme"] == "Java"
        assert vQuestion["position"] == vIndex + 1

        # Première question ratée, les autres entièrement réussies
        vChecked = [] if vIndex == 0 else list(range(len(vQuestion["points"])))
        vSimulation = record_answer(database_file, vChecked + [99], NOW)

    assert get_current_question(vSimulation) is None

    vSummary = summarize_simulation(vSimulation)

    assert vSummary["score"] == 80
    assert len(vSummary["weak"]) == 1
    assert get_history(database_file)[0]["score"] == 80
    assert [
        vQuestion["question"] for vQuestion in get_weak_questions(database_file)
    ] == (vSummary["weak"])
    assert any(
        vCard["origin"] == "Simulation technique · Java"
        and "Points clés :" in vCard["answer"]
        for vCard in build_deck(database_file)
    )

    with pytest.raises(ValueError, match="Aucune simulation"):
        record_answer(database_file, [0], NOW)

    stop_simulation(database_file)

    assert load_simulation(database_file) is None
