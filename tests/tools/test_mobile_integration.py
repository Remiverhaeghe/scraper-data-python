"""Tests de la préparation du test d'intégration téléphone ↔ serveur"""

from datetime import datetime

import tools.mobile_integration as mobile_integration
from job.interview_simulation import load_interview_questions, record_phone_series
from job.mobile_sync import build_offer_list, sync_status_changes
from job.quiz import flag_question, load_quiz
from job.quiz_exam import merge_exam_results
from job.self_assessment import save_skill_levels
from storage.quiz_answers import save_quiz_answer


def test_prepare_refuses_an_existing_database(tmp_path, monkeypatch, capsys):
    """Vérifie qu'une base existante, peut-être la vraie, garde son jeton."""

    vDatabaseFile = tmp_path / "scraper.db"
    monkeypatch.setattr(mobile_integration, "DATABASE_FILE", str(vDatabaseFile))

    assert mobile_integration.prepare() == 0
    assert len(capsys.readouterr().out.strip()) >= 40
    assert mobile_integration.prepare() == 1
    assert "existe déjà" in capsys.readouterr().out


def test_check_needs_everything_the_phone_sends(tmp_path, monkeypatch, capsys):
    """Vérifie le contrôle : il échoue tant que tout n'est pas reçu."""

    vDatabaseFile = tmp_path / "scraper.db"
    monkeypatch.setattr(mobile_integration, "DATABASE_FILE", str(vDatabaseFile))
    mobile_integration.prepare()
    vOffers = build_offer_list(vDatabaseFile, datetime.now())
    vQuestionId = load_quiz()["sql"]["questions"][0]["id"]

    assert vOffers[0]["covered"] == ["Java", "SQL"]
    assert vOffers[0]["missing"] == ["Docker"]
    assert mobile_integration.check() == 1
    assert "auto-évaluation absente" in capsys.readouterr().out

    save_quiz_answer(vDatabaseFile, vQuestionId, "sql", True, datetime.now())
    flag_question(vDatabaseFile, vQuestionId)
    merge_exam_results(
        vDatabaseFile,
        [{"finished_at": "2026-10-22T18:30:00", "score": 75, "device": "téléphone"}],
    )
    record_phone_series(
        vDatabaseFile,
        [
            {
                "theme": "Java",
                "results": [
                    {
                        "question_id": next(iter(load_interview_questions())),
                        "checked": [0],
                    }
                ],
            }
        ],
        datetime.now(),
    )
    save_skill_levels(vDatabaseFile, {"Java": 6})
    sync_status_changes(
        vDatabaseFile,
        [{"source": "adzuna", "source_id": "integration", "status": "INTERESTED"}],
        datetime.now(),
    )

    assert mobile_integration.check() == 0
