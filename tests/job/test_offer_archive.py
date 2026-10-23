"""Tests de l'archivage des offres expirées"""

from datetime import datetime, timedelta

import pandas as pd

from job.offer_archive import archive_expired_offers, find_offers_to_archive
from job.settings import save_settings
from storage.backup import list_backups
from storage.database import initialize_database
from storage.job_applications import save_application
from storage.job_offers import get_offers, save_offers

NOW = datetime(2026, 10, 23, 12)


def test_expired_offers_are_archived_once_a_day_except_followed_ones(tmp_path):
    """Vérifie l'archivage : délai réglé, offres suivies gardées, une fois par jour."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)

    for vId, vDays in (("ancienne", 400), ("suivie", 400), ("recente", 10)):
        save_offers(
            vDatabaseFile,
            pd.DataFrame([{"source": "lever", "source_id": vId, "title": "Offre"}]),
            NOW - timedelta(days=vDays),
        )

    save_application(vDatabaseFile, "lever", "suivie", "INTERESTED", pNow=NOW)

    assert find_offers_to_archive(vDatabaseFile, NOW) == []
    assert archive_expired_offers(vDatabaseFile, NOW) == 0

    save_settings(vDatabaseFile, {"archive_after_days": "180"})

    # Déjà fait aujourd'hui : rien avant demain
    assert archive_expired_offers(vDatabaseFile, NOW) == 0
    assert archive_expired_offers(vDatabaseFile, NOW + timedelta(days=1)) == 1
    assert sorted(get_offers(vDatabaseFile)["source_id"]) == ["recente", "suivie"]
    assert list_backups(vDatabaseFile)


def test_archive_delay_never_goes_below_expiry(tmp_path):
    """Vérifie qu'un délai plus court que l'expiration ne touche pas une offre active."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    save_offers(
        vDatabaseFile,
        pd.DataFrame([{"source": "lever", "source_id": "1", "title": "Offre"}]),
        NOW - timedelta(days=5),
    )
    save_settings(vDatabaseFile, {"archive_after_days": "1"})

    assert find_offers_to_archive(vDatabaseFile, NOW) == []
