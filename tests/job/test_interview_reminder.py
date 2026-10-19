"""Tests du rappel la veille d'un entretien"""

from datetime import datetime, timedelta

import pandas as pd
import pytest

import scheduler.runner as runner
from job.interview_reminder import build_reminder_email, get_interviews_to_remind
from job.profile import build_profile, save_profile
from job.schedule import save_notification_email
from job.star_answers import save_star_answer
from storage.database import initialize_database
from storage.job_applications import save_application
from storage.job_offers import save_offers

NOW = datetime(2026, 10, 19, 18, 0)


@pytest.fixture
def database_file(tmp_path):
    """Crée deux entretiens : demain matin et dans une semaine."""

    rDatabaseFile = tmp_path / "scraper.db"

    initialize_database(rDatabaseFile)
    save_offers(
        rDatabaseFile,
        pd.DataFrame(
            [
                {
                    "source": "remotive",
                    "source_id": vId,
                    "title": f"Développeur {vId}",
                    "company": "Acme",
                    "description": "Équipe agile, délais courts.",
                }
                for vId in ("1", "2")
            ]
        ),
        NOW,
    )

    for vId, vDays in (("1", 0.6), ("2", 7)):
        save_application(
            rDatabaseFile,
            "remotive",
            vId,
            "INTERVIEW",
            pNow=NOW,
            pInterviewAt=NOW + timedelta(days=vDays),
        )

    save_profile(rDatabaseFile, build_profile("", "", "Python", "Dev | Python | x", ""))
    save_star_answer(rDatabaseFile, "pression", "Dev", {"action": "Priorisé"})

    return rDatabaseFile


def test_reminder_lists_preparation(database_file):
    """Vérifie l'entretien retenu et le contenu du rappel."""

    vInterviews = get_interviews_to_remind(database_file, NOW)

    assert [vItem["source_id"] for vItem in vInterviews] == ["1"]

    vSubject, vText, _ = build_reminder_email(database_file, vInterviews[0])

    assert vSubject.endswith("entretien demain, Développeur 1")
    assert "Entretien le 20/10/2026 pour le poste de Développeur 1 chez Acme" in vText
    assert "travail en équipe" not in vText
    assert "Comment avez-vous géré un désaccord dans une équipe ? (à préparer)" in vText
    assert "Action : Priorisé" in vText


def test_reminder_is_sent_once(database_file, monkeypatch):
    """Vérifie l'envoi unique du rappel par le planificateur."""

    vSent = []

    save_notification_email(database_file, "moi@example.com")
    monkeypatch.setattr(runner, "send_email", lambda *pArgs: vSent.append(pArgs))

    assert runner.send_interview_reminders(database_file, NOW) == 1
    assert runner.send_interview_reminders(database_file, NOW) == 0
    assert len(vSent) == 1
