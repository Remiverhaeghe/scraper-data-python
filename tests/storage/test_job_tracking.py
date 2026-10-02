# ============================================================================
# Tests du suivi des offres d'emploi
# ============================================================================


from datetime import datetime
from pathlib import Path

import pandas as pd

from storage.database import initialize_database
from storage.job_tracking import track_jobs


def build_items():
    """
    Construit un DataFrame minimal pour les tests.

    :return: DataFrame de test.
    """

    rItems = pd.DataFrame(
        [
            {
                "source": "lever",
                "source_id": "123",
                "title": "Développeur Python"
            }
        ]
    )

    return rItems


def test_new_job_gets_first_seen_at(tmp_path):
    """
    Vérifie qu'une nouvelle offre reçoit une date de première découverte.
    """

    vDatabaseFile = Path(
        tmp_path
    ) / "scraper.db"

    initialize_database(
        vDatabaseFile
    )

    vScrapedAt = datetime(
        2026,
        10,
        1,
        10,
        0,
        0
    )

    vItems = track_jobs(
        vDatabaseFile,
        build_items(),
        vScrapedAt
    )

    assert vItems.loc[
        0,
        "scraped_at"
    ] == vScrapedAt

    assert vItems.loc[
        0,
        "first_seen_at"
    ] == vScrapedAt


def test_existing_job_keeps_first_seen_at(tmp_path):
    """
    Vérifie que la première date reste inchangée
    lors d'une nouvelle récupération.
    """

    vDatabaseFile = Path(
        tmp_path
    ) / "scraper.db"

    initialize_database(
        vDatabaseFile
    )

    vFirstScrapedAt = datetime(
        2026,
        10,
        1,
        10,
        0,
        0
    )

    vSecondScrapedAt = datetime(
        2026,
        10,
        2,
        10,
        0,
        0
    )

    vItems = build_items()

    track_jobs(
        vDatabaseFile,
        vItems,
        vFirstScrapedAt
    )

    vItems = track_jobs(
        vDatabaseFile,
        vItems,
        vSecondScrapedAt
    )

    assert vItems.loc[
        0,
        "first_seen_at"
    ] == vFirstScrapedAt

    assert vItems.loc[
        0,
        "scraped_at"
    ] == vSecondScrapedAt


def test_same_source_id_is_tracked_separately(tmp_path):
    """
    Vérifie qu'un même source_id provenant de deux sources
    différentes correspond à deux offres différentes.
    """

    vDatabaseFile = Path(
        tmp_path
    ) / "scraper.db"

    initialize_database(
        vDatabaseFile
    )

    vScrapedAt = datetime(
        2026,
        10,
        1,
        10,
        0,
        0
    )

    vItems = pd.DataFrame(
        [
            {
                "source": "lever",
                "source_id": "123",
                "title": "Offre Lever"
            },
            {
                "source": "greenhouse",
                "source_id": "123",
                "title": "Offre Greenhouse"
            }
        ]
    )

    vResult = track_jobs(
        vDatabaseFile,
        vItems,
        vScrapedAt
    )

    assert vResult.loc[
        0,
        "first_seen_at"
    ] == vScrapedAt

    assert vResult.loc[
        1,
        "first_seen_at"
    ] == vScrapedAt