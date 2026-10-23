"""Tests de la préparation du test d'intégration téléphone ↔ serveur"""

from datetime import datetime

import tools.mobile_integration as mobile_integration
from job.quiz import flag_question, load_quiz
from job.quiz_exam import merge_exam_results
from storage.database import initialize_database
from storage.quiz_answers import save_quiz_answer


def test_prepare_refuses_an_existing_database(tmp_path, monkeypatch, capsys):
    """Vérifie qu'une base existante, peut-être la vraie, garde son jeton."""

    vDatabaseFile = tmp_path / "scraper.db"
    monkeypatch.setattr(mobile_integration, "DATABASE_FILE", str(vDatabaseFile))

    assert mobile_integration.prepare() == 0
    assert len(capsys.readouterr().out.strip()) >= 40
    assert mobile_integration.prepare() == 1
    assert "existe déjà" in capsys.readouterr().out


def test_check_needs_answer_flag_and_exam(tmp_path, monkeypatch):
    """Vérifie le contrôle : il échoue tant que tout n'est pas reçu."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    monkeypatch.setattr(mobile_integration, "DATABASE_FILE", str(vDatabaseFile))
    vQuestionId = load_quiz()["sql"]["questions"][0]["id"]

    assert mobile_integration.check() == 1

    save_quiz_answer(vDatabaseFile, vQuestionId, "sql", True, datetime.now())
    flag_question(vDatabaseFile, vQuestionId)
    merge_exam_results(
        vDatabaseFile,
        [{"finished_at": "2026-10-22T18:30:00", "score": 75, "device": "téléphone"}],
    )

    assert mobile_integration.check() == 0
