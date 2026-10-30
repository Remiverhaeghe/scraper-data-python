"""Tests des trophées et de la carte joueur"""

from datetime import date, timedelta

from job.achievements import (
    HEATMAP_WEEKS,
    build_player_card,
    evaluate_achievements,
    get_heat_level,
    has_comeback,
    has_weekend,
    sort_achievements,
)
from storage.database import initialize_database

TODAY = date(2026, 10, 30)
PROGRESS = {"best_streak": 1, "level": 1}


def activity(pDays):
    """Construit une activité : un jour par entrée (date, réponses justes, XP)."""

    rActivity = {
        vDay: {"xp": vXp, "actions": {"answer_right": vCount}}
        for vDay, vCount, vXp in pDays
    }

    return rActivity


def test_trophy_is_dated_once_and_hidden_until_unlocked(tmp_path):
    """Vérifie le trophée daté à son obtention, puis gardé ; le caché reste masqué."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    vActivity = activity([(TODAY, 1, 5)])

    vFirst = {
        vItem["id"]: vItem
        for vItem in evaluate_achievements(vDatabaseFile, vActivity, PROGRESS, TODAY)
    }
    vLater = {
        vItem["id"]: vItem
        for vItem in evaluate_achievements(
            vDatabaseFile, vActivity, PROGRESS, TODAY + timedelta(days=3)
        )
    }

    assert vFirst["first-answer"]["unlocked_on"] == TODAY.isoformat()
    assert vLater["first-answer"]["unlocked_on"] == TODAY.isoformat()
    assert vFirst["answers-100"]["progress"] == 1
    assert vFirst["big-day"]["title"] == "Trophée caché"
    assert not vFirst["big-day"]["unlocked"]


def test_hidden_trophies_detect_weekend_and_comeback():
    """Vérifie le week-end actif et le retour après une semaine sans activité."""

    vSaturday = date(2026, 10, 24)

    assert has_weekend([vSaturday, vSaturday + timedelta(days=1)])
    assert not has_weekend(
        [vSaturday + timedelta(days=1), vSaturday + timedelta(days=7)]
    )
    assert has_comeback([TODAY - timedelta(days=10), TODAY])
    assert not has_comeback([TODAY - timedelta(days=7), TODAY])


def test_player_card_has_records_and_twelve_weeks(tmp_path):
    """Vérifie la carte joueur : records et une case par jour, futur sans valeur."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    vCard = build_player_card(
        vDatabaseFile, activity([(TODAY, 3, 15)]), PROGRESS, TODAY
    )

    assert len(vCard["heatmap"]) == 7 * HEATMAP_WEEKS
    assert vCard["heatmap"][-1]["xp"] is None
    assert {"label": "Réponses de révision", "value": 3} in vCard["records"]
    assert [get_heat_level(vXp) for vXp in (0, 10, 50, 100, 300)] == [0, 1, 2, 3, 4]


def test_unlocked_trophies_come_first_most_recent_first():
    """Vérifie l'ordre d'affichage des trophées."""

    vSorted = sort_achievements(
        [
            {"id": "a", "unlocked": False, "unlocked_on": None},
            {"id": "b", "unlocked": True, "unlocked_on": "2026-10-01"},
            {"id": "c", "unlocked": True, "unlocked_on": "2026-10-20"},
        ]
    )

    assert [vItem["id"] for vItem in vSorted] == ["c", "b", "a"]
