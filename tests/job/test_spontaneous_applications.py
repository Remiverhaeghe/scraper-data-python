"""Tests du suivi des candidatures spontanées"""

from datetime import date

import pytest

from job.progress import get_total_xp
from job.spontaneous_applications import (
    describe_spontaneous,
    get_contact_tone,
    list_due_follow_ups,
    load_spontaneous,
    save_spontaneous,
)
from storage.database import initialize_database

SENT_ON = date(2026, 10, 1)


@pytest.fixture
def database_file(tmp_path):
    """Crée une base vide."""

    rDatabaseFile = tmp_path / "scraper.db"
    initialize_database(rDatabaseFile)

    return rDatabaseFile


def test_steps_keep_the_first_sending_date(database_file):
    """Vérifie l'envoi, la relance datée, la réponse, la note bornée et le retrait."""

    save_spontaneous(database_file, "1", "Roquette", "sent", SENT_ON, "Par e-mail")
    save_spontaneous(database_file, "1", "Roquette", "followed_up", date(2026, 10, 16))
    save_spontaneous(
        database_file, "1", "Roquette", "interview", date(2026, 10, 20), "x" * 900
    )

    assert load_spontaneous(database_file)["1"] == {
        "name": "Roquette",
        "status": "interview",
        "sent_on": "2026-10-01",
        "followed_up_on": "2026-10-16",
        "answered_on": "2026-10-20",
        "note": "x" * 500,
    }

    save_spontaneous(database_file, "1", "Roquette", "", SENT_ON)

    assert load_spontaneous(database_file) == {}

    with pytest.raises(ValueError):
        save_spontaneous(database_file, "1", "Roquette", "oublié", SENT_ON)


def test_follow_up_is_due_after_fifteen_days_without_answer(database_file):
    """Vérifie la relance due au quinzième jour, repoussée par une relance faite."""

    save_spontaneous(database_file, "1", "Roquette", "sent", SENT_ON)
    save_spontaneous(database_file, "2", "Alstom", "refused", SENT_ON)

    assert list_due_follow_ups(database_file, date(2026, 10, 15)) == []

    vDue = list_due_follow_ups(database_file, date(2026, 10, 16))

    assert [vItem["siren"] for vItem in vDue] == ["1"]
    assert vDue[0]["status_label"] == "Envoyée"

    save_spontaneous(database_file, "1", "Roquette", "followed_up", date(2026, 10, 16))

    assert list_due_follow_ups(database_file, date(2026, 10, 30)) == []
    assert describe_spontaneous(None, SENT_ON) is None


def test_tone_follows_the_step():
    """Vérifie la teinte sur la carte : à contacter, envoyée, à relancer, réponse."""

    def tone(pStatus, pDue=False):
        return get_contact_tone({"status": pStatus, "follow_up_due": pDue})

    assert get_contact_tone(None) == "primary"
    assert tone("sent") == "warning" and tone("sent", True) == "danger"
    assert tone("interview") == "success" and tone("refused") == "muted"


def test_sending_and_follow_up_earn_points(database_file):
    """Vérifie les points de l'envoi, de la relance et de l'entretien obtenu."""

    save_spontaneous(database_file, "1", "Roquette", "sent", SENT_ON)
    save_spontaneous(database_file, "1", "Roquette", "followed_up", date(2026, 10, 16))
    save_spontaneous(database_file, "2", "Alstom", "interview", SENT_ON)

    assert get_total_xp(database_file) == 30 + 15 + 30 + 100
