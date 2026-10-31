"""Tests de la mission d'entretien : étapes cochées, manques, boss et récompense"""

from datetime import datetime

import pytest

from job.interview_mission import build_mission, load_missions, set_step
from job.progress import load_activity
from job.quiz_exam import EXAM_RESULTS_KEY
from storage.database import initialize_database
from storage.settings_repository import save_json_setting

NOW = datetime(2026, 10, 31, 9, 0)
OFFER = {
    "source": "adzuna",
    "source_id": "42",
    "title": "Technicien",
    "company": "Acme",
}


@pytest.fixture
def database_file(tmp_path):
    """Fournit une base vide."""

    rDatabaseFile = tmp_path / "scraper.db"
    initialize_database(rDatabaseFile)

    return rDatabaseFile


def save_exams(pDatabaseFile, *pResults):
    """Enregistre des notes d'examens blancs."""

    save_json_setting(pDatabaseFile, EXAM_RESULTS_KEY, list(pResults))


def test_new_mission_starts_empty(database_file):
    """Vérifie une mission neuve : rien de fait, manques et boss à affronter."""

    vMission = build_mission(database_file, OFFER, ["Python"])

    assert (vMission["done"], vMission["total"], vMission["percent"]) == (0, 6, 0)
    assert vMission["steps"][3]["detail"] == "À revoir : Python."
    assert vMission["steps"][5]["detail"] == "Pas encore affronté : 70 % demandés."
    assert build_mission(database_file, OFFER, [])["steps"][3]["done"] is True


def test_automatic_steps_cannot_be_ticked(database_file):
    """Vérifie que les manques et le boss ne se cochent pas à la main."""

    for vStep in ("gaps", "boss", "inconnue"):
        with pytest.raises(ValueError):
            set_step(database_file, OFFER, vStep, True)


def test_mission_is_completed_and_rewarded_once(database_file):
    """Vérifie l'avancement, un boss trop faible, puis la récompense datée une seule fois."""

    for vStep in ("company", "pitch", "tricky", "simulation"):
        set_step(database_file, OFFER, vStep, True, NOW)

    set_step(database_file, OFFER, "pitch", False)
    set_step(database_file, OFFER, "pitch", True)
    save_exams(
        database_file,
        {
            "title": "Compétences manquantes · Entretien : Technicien chez Acme",
            "score": 40,
        },
        {"offer": ["adzuna", "42"], "score": 65, "finished_at": "2026-10-30T10:00:00"},
    )

    vMission = build_mission(database_file, OFFER, ["Python"], NOW)

    assert vMission["percent"] == 83 and vMission["boss_best"] == 65
    assert vMission["steps"][3]["detail"] == "Examen des manques passé : 40 %."

    save_exams(
        database_file,
        {
            "title": "Compétences manquantes · Entretien : Technicien chez Acme",
            "score": 40,
        },
        {"offer": ["adzuna", "42"], "score": 75, "finished_at": "2026-10-31T10:00:00"},
    )

    vDone = build_mission(database_file, OFFER, ["Python"], NOW)
    vAgain = build_mission(database_file, OFFER, ["Python"], NOW)

    assert vDone["just_completed"] and not vAgain["just_completed"]
    assert vAgain["completed_at"] == "2026-10-31T09:00:00"
    assert load_activity(database_file)[NOW.date()]["actions"]["interview_mission"] == 1

    set_step(database_file, OFFER, "pitch", False)

    assert load_missions(database_file)["adzuna/42"]["completed_at"]
    assert build_mission(database_file, OFFER, ["Python"])["percent"] == 83
