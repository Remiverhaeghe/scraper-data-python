"""Tests du récapitulatif quotidien"""

from datetime import datetime, timedelta

import pandas as pd

from job.daily_digest import (
    build_daily_digest,
    build_daily_email,
    send_daily_digest_if_due,
)
from job.settings import load_settings, save_settings
from storage.database import initialize_database
from storage.job_applications import save_application
from storage.job_offers import save_offers

NOW = datetime(2026, 10, 24, 18, 0)


def build_database(pTmpPath):
    """Crée une base avec une offre d'hier, une ancienne et un entretien demain."""

    rDatabaseFile = pTmpPath / "scraper.db"
    initialize_database(rDatabaseFile)
    save_offers(
        rDatabaseFile,
        pd.DataFrame([{"source": "lever", "source_id": "old", "title": "Ancienne"}]),
        NOW - timedelta(days=4),
    )
    save_offers(
        rDatabaseFile,
        pd.DataFrame([{"source": "lever", "source_id": "new", "title": "Nouvelle"}]),
        NOW - timedelta(hours=3),
    )
    save_application(
        rDatabaseFile,
        "lever",
        "old",
        "INTERVIEW",
        pInterviewAt=NOW + timedelta(hours=16),
    )

    return rDatabaseFile


def test_daily_digest_keeps_the_last_day_only(tmp_path):
    """Vérifie le contenu : offres de 24 heures, entretiens du lendemain."""

    vDigest = build_daily_digest(build_database(tmp_path), NOW)
    vSubject, vText, _ = build_daily_email(vDigest)

    assert [vOffer["title"] for vOffer in vDigest["offers"]] == ["Nouvelle"]
    assert len(vDigest["interviews"]) == 1
    assert vSubject.endswith("1 offre(s), 0 relance(s), 1 entretien(s)")
    assert "Nouvelles offres du jour" in vText


def test_daily_digest_is_sent_once_after_its_hour(tmp_path):
    """Vérifie l'envoi : désactivé par défaut, puis une fois par jour après l'heure."""

    vDatabaseFile = build_database(tmp_path)
    vSent = []

    def send(pEmail, pSubject, pText, pHtml):
        vSent.append(pSubject)

    assert not send_daily_digest_if_due(vDatabaseFile, NOW, "moi@exemple.fr", send)

    save_settings(
        vDatabaseFile, {**load_settings(vDatabaseFile), "daily_digest_hour": 19}
    )

    assert not send_daily_digest_if_due(vDatabaseFile, NOW, "moi@exemple.fr", send)

    vEvening = NOW.replace(hour=19, minute=5)

    assert send_daily_digest_if_due(vDatabaseFile, vEvening, "moi@exemple.fr", send)
    assert not send_daily_digest_if_due(
        vDatabaseFile, vEvening + timedelta(hours=2), "moi@exemple.fr", send
    )
    assert len(vSent) == 1
