"""Tests de la comparaison des offres"""

from datetime import datetime

import pandas as pd
import pytest

from job.offer_comparison import (
    build_comparison,
    clear_comparison,
    load_comparison_keys,
    toggle_comparison,
)
from job.interview_journal import record_interview
from storage.database import initialize_database
from storage.job_applications import save_application
from storage.job_offers import save_offers

NOW = datetime(2026, 10, 19, 12, 0)


@pytest.fixture
def database_file(tmp_path):
    """Crée quatre offres."""

    rDatabaseFile = tmp_path / "scraper.db"

    initialize_database(rDatabaseFile)
    save_offers(
        rDatabaseFile,
        pd.DataFrame(
            [
                {
                    "source": "remotive",
                    "source_id": str(vId),
                    "title": f"Offre {vId}",
                    "contract": "CDI",
                    "remote_days": 2 if vId == 1 else None,
                }
                for vId in range(1, 5)
            ]
        ),
        NOW,
    )

    return rDatabaseFile


def test_comparison_keeps_three_offers(database_file):
    """Vérifie la limite de trois offres, le retrait et le vidage."""

    for vId in ("1", "2", "3", "4"):
        assert toggle_comparison(database_file, "remotive", vId)

    assert load_comparison_keys(database_file) == [
        ("remotive", "2"),
        ("remotive", "3"),
        ("remotive", "4"),
    ]
    assert not toggle_comparison(database_file, "remotive", "3")
    assert len(load_comparison_keys(database_file)) == 2

    clear_comparison(database_file)

    assert load_comparison_keys(database_file) == []


def test_build_comparison_rows(database_file):
    """Vérifie une ligne par critère et l'oubli d'une offre disparue."""

    toggle_comparison(database_file, "remotive", "1")
    toggle_comparison(database_file, "remotive", "absente")

    vComparison = build_comparison(database_file, NOW)
    vRows = dict(vComparison["rows"])

    assert [vOffer["title"] for vOffer in vComparison["offers"]] == ["Offre 1"]
    assert vRows["Contrat"] == ["CDI"]
    assert vRows["Télétravail"] == ["2 jour(s) par semaine"]
    assert vRows["Fraîcheur"] == ["100 / 100"]
    assert vRows["Suivi"] == ["Aucun"]


def test_feeling_comes_from_the_interview_then_the_notes(database_file):
    """Vérifie le ressenti : impressions d'entretien d'abord, notes sinon."""

    save_application(database_file, "remotive", "1", "INTERVIEW", pNotes="Note")
    save_application(database_file, "remotive", "2", "APPLIED", pNotes="Équipe sympa")
    record_interview(database_file, "remotive", "1", NOW, "", "Très bon contact")
    toggle_comparison(database_file, "remotive", "1")
    toggle_comparison(database_file, "remotive", "2")
    toggle_comparison(database_file, "remotive", "3")

    vRows = dict(build_comparison(database_file, NOW)["rows"])

    assert vRows["Mon ressenti"] == ["Très bon contact", "Équipe sympa", "Non noté"]
    assert vRows["Net après trajet"] == ["Non calculé"] * 3
    assert vRows["Avantages"] == ["Aucun repéré"] * 3
