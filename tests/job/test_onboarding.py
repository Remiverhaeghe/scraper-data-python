"""Tests des premiers pas : quêtes cochées d'elles-mêmes, récompense unique, visite"""

from datetime import datetime

from job.mobile_sync import LAST_SYNC_KEY
from job.onboarding import TOUR_STEPS, build_start_quests, build_tour
from job.profile import load_profile, save_profile
from job.progress import load_activity
from scraper.history import HistoryEntry
from storage.database import initialize_database
from storage.history_repository import save_history
from storage.quiz_answers import save_quiz_answer
from storage.saved_searches import save_search
from storage.settings_repository import save_setting_values

NOW = datetime(2026, 10, 31, 9, 0)


def test_start_quests_tick_themselves_and_reward_once(tmp_path):
    """Vérifie chaque quête cochée d'après les données, puis la récompense datée une fois."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)

    assert build_start_quests(vDatabaseFile, NOW)["done"] == 0

    save_profile(vDatabaseFile, {**load_profile(vDatabaseFile), "skills": ["Python"]})
    save_search(
        vDatabaseFile, "Automatisme", ["remotive"], {"keyword": "automate"}, NOW
    )
    save_history(
        vDatabaseFile,
        HistoryEntry(
            started_at=NOW,
            scraper_type="job",
            url="multi-source",
            page_count=1,
            item_count=3,
            duration_seconds=1.0,
            status="success",
        ),
    )
    save_quiz_answer(vDatabaseFile, "q1", "python", True, NOW)

    vStart = build_start_quests(vDatabaseFile, NOW)

    assert (vStart["done"], vStart["completed_at"]) == (4, None)
    assert [vQuest["done"] for vQuest in vStart["quests"]] == [True] * 4 + [False]

    save_setting_values(vDatabaseFile, {LAST_SYNC_KEY: NOW.isoformat()})

    assert build_start_quests(vDatabaseFile, NOW)["completed_at"] == NOW.isoformat()
    assert build_start_quests(vDatabaseFile, datetime(2026, 11, 2))["completed_at"] == (
        NOW.isoformat()
    )
    assert load_activity(vDatabaseFile)[NOW.date()]["actions"]["onboarding"] == 1


def test_tour_visits_every_main_page_with_the_mascot():
    """Vérifie les étapes de la visite : page, texte, dessin et numérotation."""

    vTour = build_tour()

    assert [vStep["page"] for vStep in vTour] == [vStep[0] for vStep in TOUR_STEPS]
    assert vTour[0]["page"] == "home" and vTour[-1]["position"] == len(TOUR_STEPS)
    assert all("<svg" in vStep["svg"] for vStep in vTour)
