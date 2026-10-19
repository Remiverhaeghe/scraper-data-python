"""Tests de l'entraînement à l'oral"""

from datetime import datetime, timedelta

import pandas as pd
import pytest

from job.interview_drill import build_deck, get_due_cards, grade_card
from job.interview_journal import record_interview
from job.star_answers import save_star_answer
from storage.database import initialize_database
from storage.job_offers import save_offers

NOW = datetime(2026, 10, 19, 9, 0)


@pytest.fixture
def database_file(tmp_path):
    """Crée une réponse STAR et une question vécue en entretien."""

    rDatabaseFile = tmp_path / "scraper.db"

    initialize_database(rDatabaseFile)
    save_offers(
        rDatabaseFile,
        pd.DataFrame([{"source": "remotive", "source_id": "1", "title": "Dev"}]),
        NOW,
    )
    save_star_answer(rDatabaseFile, "echec", "", {"result": "Leçon retenue"})
    record_interview(rDatabaseFile, "remotive", "1", NOW, "Pourquoi nous ?", "")

    return rDatabaseFile


def test_deck_and_spaced_review(database_file):
    """Vérifie les cartes, leur réponse et leur retour selon l'auto-évaluation."""

    vDeck = build_deck(database_file)

    assert [vCard["origin"].split(" :")[0] for vCard in vDeck] == [
        "Réponse STAR",
        "Posée en entretien",
    ]
    assert vDeck[0]["answer"] == "Résultat : Leçon retenue"
    assert len(get_due_cards(database_file, NOW)) == 2

    grade_card(database_file, vDeck[0]["id"], True, NOW)
    grade_card(database_file, vDeck[1]["id"], False, NOW)

    assert get_due_cards(database_file, NOW) == []
    assert [
        vCard["id"] for vCard in get_due_cards(database_file, NOW + timedelta(days=1))
    ] == [
        vDeck[0]["id"],
        vDeck[1]["id"],
    ]

    grade_card(database_file, vDeck[0]["id"], True, NOW + timedelta(days=1))

    assert vDeck[0]["id"] not in [
        vCard["id"] for vCard in get_due_cards(database_file, NOW + timedelta(days=3))
    ]
