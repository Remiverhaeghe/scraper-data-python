"""Tests du journal d'entretien"""

from datetime import datetime

import pandas as pd
import pytest

from job.interview_journal import (
    collect_asked_questions,
    record_interview,
    split_questions,
)
from job.offer_purge import find_offers_to_purge
from storage.database import initialize_database
from storage.interview_notes import delete_interview_note, get_interview_notes
from storage.job_offers import save_offers
from storage.maintenance import reset_database

NOW = datetime(2026, 10, 19, 14, 30)


@pytest.fixture
def database_file(tmp_path):
    """Crée une base avec une offre."""

    rDatabaseFile = tmp_path / "scraper.db"

    initialize_database(rDatabaseFile)
    save_offers(
        rDatabaseFile,
        pd.DataFrame(
            [
                {
                    "source": "remotive",
                    "source_id": "1",
                    "title": "Stage Java",
                    "company": "Acme",
                }
            ]
        ),
        NOW,
    )

    return rDatabaseFile


def test_split_questions_removes_bullets_and_duplicates():
    """Vérifie le découpage ligne à ligne, sans puces ni doublons."""

    assert split_questions(
        "- Parlez de vous\n\n• Pourquoi nous ?\n- Parlez de vous"
    ) == [
        "Parlez de vous",
        "Pourquoi nous ?",
    ]


def test_interview_is_recorded_collected_and_protected(database_file):
    """Vérifie l'enregistrement, la reprise des questions et la protection à la purge."""

    with pytest.raises(ValueError, match="au moins une question"):
        record_interview(database_file, "remotive", "1", NOW, " ", "")

    vNoteId = record_interview(
        database_file, "remotive", "1", NOW, "Un conflit vécu ?", "Bon échange"
    )

    assert collect_asked_questions(database_file) == [
        {"question": "Un conflit vécu ?", "context": "19/10/2026 · Stage Java · Acme"}
    ]
    assert find_offers_to_purge(database_file, ["stage"]) == []

    delete_interview_note(database_file, vNoteId)

    assert get_interview_notes(database_file) == []


def test_reset_clears_the_journal(database_file):
    """Vérifie que la réinitialisation vide aussi le journal."""

    record_interview(database_file, "remotive", "1", NOW, "Question", "")

    reset_database(database_file, NOW)

    assert get_interview_notes(database_file) == []
