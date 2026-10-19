"""Tests du récapitulatif hebdomadaire"""

from datetime import datetime, timedelta

import pandas as pd
import pytest

import scheduler.runner as runner
from job.profile import build_profile, save_profile
from job.schedule import save_notification_email
from job.weekly_digest import (
    build_digest_email,
    build_weekly_digest,
    get_week_key,
    is_digest_due,
)
from storage.database import initialize_database
from storage.job_applications import save_application
from storage.job_offers import save_offers

NOW = datetime(2026, 10, 19, 8, 0)


@pytest.fixture
def database_file(tmp_path):
    """Crée deux offres récentes, dont une en entretien dans trois jours."""

    rDatabaseFile = tmp_path / "scraper.db"

    initialize_database(rDatabaseFile)
    save_offers(
        rDatabaseFile,
        pd.DataFrame(
            [
                {
                    "source": "remotive",
                    "source_id": "1",
                    "title": "Développeur Python",
                    "description": "Python et SQL",
                    "url": "https://example.com/1",
                },
                {
                    "source": "remotive",
                    "source_id": "2",
                    "title": "<b>Chef de projet</b>",
                    "company": "Acme",
                },
            ]
        ),
        NOW - timedelta(days=2),
    )
    save_application(
        rDatabaseFile,
        "remotive",
        "2",
        "INTERVIEW",
        pNow=NOW,
        pInterviewAt=NOW + timedelta(days=3),
    )
    save_profile(rDatabaseFile, build_profile("", "", "Python", "", ""))

    return rDatabaseFile


def test_digest_gathers_offers_interviews_and_preparation(database_file):
    """Vérifie le contenu du récapitulatif et l'échappement du HTML."""

    vDigest = build_weekly_digest(database_file, NOW)
    vSubject, vText, vHtml = build_digest_email(vDigest)

    assert vDigest["offers"][0]["title"] == "Développeur Python"
    assert [vItem["source_id"] for vItem in vDigest["interviews"]] == ["2"]
    assert vSubject.endswith("2 offre(s), 0 relance(s), 1 entretien(s)")
    assert "Entretiens à venir" in vText
    assert "le 22/10/2026 · Acme" in vText
    assert "&lt;b&gt;Chef de projet&lt;/b&gt;" in vHtml
    assert "Préparation des compétences demandées" in vText


def test_digest_is_sent_once_a_week(database_file, monkeypatch):
    """Vérifie l'envoi au premier passage de la semaine, puis plus avant la suivante."""

    vSent = []

    save_notification_email(database_file, "moi@example.com")
    monkeypatch.setattr(runner, "send_email", lambda *pArgs: vSent.append(pArgs))

    assert get_week_key(NOW) == "2026-W43"
    assert runner.send_weekly_digest(database_file, NOW)
    assert not runner.send_weekly_digest(database_file, NOW + timedelta(days=2))
    assert is_digest_due(database_file, NOW + timedelta(days=7))
    assert len(vSent) == 1
