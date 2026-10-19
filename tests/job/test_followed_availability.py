"""Tests de la vérification quotidienne des offres suivies"""

from datetime import datetime, timedelta

import pandas as pd
import pytest

import scheduler.runner as runner
from job.application_tracking import build_board
from job.followed_availability import (
    build_expired_offers_email,
    check_followed_offers,
    run_due_followed_check,
)
from job.schedule import save_notification_email
from storage.database import initialize_database
from storage.job_applications import save_application
from storage.job_offers import get_offer, save_offers

NOW = datetime(2026, 10, 19, 8, 0)


@pytest.fixture
def database_file(tmp_path):
    """Crée trois offres : suivie, suivie sans conclusion et non suivie."""

    rDatabaseFile = tmp_path / "scraper.db"

    initialize_database(rDatabaseFile)
    save_offers(
        rDatabaseFile,
        pd.DataFrame(
            [
                {
                    "source": "remotive",
                    "source_id": vId,
                    "title": f"Offre {vId}",
                    "company": "Acme",
                    "url": f"https://example.com/{vId}",
                }
                for vId in ("1", "2", "3")
            ]
        ),
        NOW - timedelta(days=3),
    )
    save_application(rDatabaseFile, "remotive", "1", "APPLIED", pNow=NOW)
    save_application(rDatabaseFile, "remotive", "2", "INTERESTED", pNow=NOW)

    return rDatabaseFile


def fake_check(pUrl):
    """Simule le site : l'offre 1 est retirée, le site de l'offre 2 ne répond pas."""

    rAvailability = "expired" if pUrl.endswith("/1") else None

    return rAvailability


def test_followed_offers_are_checked_once_a_day(database_file):
    """Vérifie le passage quotidien, l'offre retirée et l'absence de conclusion."""

    vChecked = []

    def recording_check(pUrl):
        vChecked.append(pUrl)

        return fake_check(pUrl)

    vExpired = run_due_followed_check(database_file, NOW, recording_check)

    assert [vOffer["source_id"] for vOffer in vExpired] == ["1"]
    assert sorted(vChecked) == ["https://example.com/1", "https://example.com/2"]
    assert get_offer(database_file, "remotive", "1")["availability"] == "expired"
    assert get_offer(database_file, "remotive", "2")["availability"] is None
    assert run_due_followed_check(database_file, NOW, recording_check) == []
    assert len(vChecked) == 2

    vCards = [
        vCard
        for vColumn in build_board(database_file, NOW)
        for vCard in vColumn["cards"]
    ]

    assert {vCard["source_id"]: vCard["expired"] for vCard in vCards} == {
        "1": True,
        "2": False,
    }

    # L'offre déjà retirée n'est plus vérifiée, la seconde l'est de nouveau.
    assert (
        check_followed_offers(database_file, NOW + timedelta(days=1), recording_check)
        == []
    )
    assert vChecked[-1] == "https://example.com/2"


def test_expired_offers_email_and_alert(database_file, monkeypatch):
    """Vérifie l'e-mail des offres retirées envoyé par le planificateur."""

    vSent = []

    save_notification_email(database_file, "moi@example.com")
    monkeypatch.setattr(runner, "send_email", lambda *pArgs: vSent.append(pArgs))
    monkeypatch.setattr(
        runner,
        "run_due_followed_check",
        lambda pDatabaseFile, pNow: check_followed_offers(
            pDatabaseFile, pNow, fake_check
        ),
    )

    assert runner.check_followed_offers_daily(database_file, NOW)
    assert vSent[0][0] == "moi@example.com"
    assert "1 offre(s) suivie(s) retirée(s)" in vSent[0][1]
    assert (
        "Acme · Postulé"
        in build_expired_offers_email(
            [{"title": "Offre", "company": "Acme", "status": "APPLIED", "url": None}]
        )[1]
    )
