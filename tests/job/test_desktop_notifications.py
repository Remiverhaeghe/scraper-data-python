"""Tests des notifications du bureau : choix, heures calmes, plafond, pas de répétition"""

from datetime import datetime

import pytest

import job.desktop_notifications as notifications
from job.desktop_notifications import is_quiet, pick_notification
from job.page_timings import record_page_time
from job.settings import load_settings, save_settings
from storage.database import initialize_database

MORNING = datetime(2026, 10, 31, 10, 0)
EVENING = datetime(2026, 10, 31, 20, 0)
QUEST = {"id": "answers", "weekly": False, "done": False, "progress": 7, "target": 10}


@pytest.fixture
def database_file(tmp_path, monkeypatch):
    """Fournit une base vide et une situation fixe : relance, offre, quête, série."""

    rDatabaseFile = tmp_path / "scraper.db"
    initialize_database(rDatabaseFile)
    monkeypatch.setattr(
        notifications,
        "get_due_follow_ups",
        lambda *pArgs: [{"title": "Technicien", "company": "Acme"}],
    )
    monkeypatch.setattr(
        notifications,
        "find_hot_offers",
        lambda *pArgs: [
            {
                "source": "lever",
                "source_id": "1",
                "title": "Automaticien",
                "match_score": 85,
            },
            {
                "source": "lever",
                "source_id": "2",
                "title": "Électricien",
                "match_score": 72,
            },
        ],
    )
    monkeypatch.setattr(notifications, "find_preferred_offers", lambda *pArgs: [])
    monkeypatch.setattr(
        notifications,
        "build_progress",
        lambda *pArgs: {
            "quests": [{**QUEST, "label": "Répondre à 10 questions"}],
            "streak": 4,
            "active_today": False,
        },
    )

    return rDatabaseFile


@pytest.mark.parametrize(
    "pHour, pStart, pEnd, pExpected",
    [
        (22, 21, 8, True),
        (3, 21, 8, True),
        (8, 21, 8, False),
        (14, 12, 14, False),
        (12, 12, 14, True),
        (5, 0, 0, False),
    ],
)
def test_quiet_hours_may_span_midnight(pHour, pStart, pEnd, pExpected):
    """Vérifie les heures calmes, de part et d'autre de minuit ou non."""

    assert is_quiet(pHour, pStart, pEnd) is pExpected


def test_three_notifications_a_day_at_most_and_never_twice(database_file):
    """Vérifie l'ordre d'utilité, le plafond du jour et l'absence de répétition."""

    vShown = [pick_notification(database_file, MORNING) for _ in range(4)]

    assert [vItem["page"] for vItem in vShown[:3]] == [
        "applications",
        "offers",
        "progress",
    ]
    assert vShown[0]["text"] == "Technicien chez Acme"
    assert vShown[1]["title"] == "Offre à 85 % de votre profil"
    assert vShown[2]["text"] == "Plus que 3 pour « Répondre à 10 questions »"
    assert vShown[3] is None

    vNextDay = pick_notification(database_file, MORNING.replace(day=1, month=11))

    assert vNextDay["key"].startswith("follow-ups-2026-11-01")


def test_evening_streak_and_quiet_hours(database_file):
    """Vérifie la série en danger le soir, puis le silence des heures calmes."""

    vSettings = load_settings(database_file)
    save_settings(
        database_file,
        {**vSettings, "notification_daily_limit": 10, "notification_quiet_start": 22},
    )

    vShown = [pick_notification(database_file, EVENING) for _ in range(4)]

    assert (
        vShown[3]["title"] == "Série de 4 jours en danger"
        and vShown[3]["page"] == "quiz"
    )
    assert pick_notification(database_file, EVENING.replace(hour=23)) is None

    save_settings(database_file, {**vSettings, "notification_daily_limit": 0})

    assert pick_notification(database_file, MORNING.replace(day=2, month=11)) is None


def test_new_offer_of_a_followed_employer_is_announced(database_file, monkeypatch):
    """Vérifie la notification d'une nouvelle offre chez un employeur suivi."""

    monkeypatch.setattr(notifications, "get_due_follow_ups", lambda *pArgs: [])
    monkeypatch.setattr(notifications, "find_hot_offers", lambda *pArgs: [])
    monkeypatch.setattr(
        notifications,
        "find_preferred_offers",
        lambda *pArgs: [
            {
                "source": "lever",
                "source_id": "9",
                "company": "Roquette",
                "title": "Technicien de maintenance",
            }
        ],
    )

    vNotification = pick_notification(database_file, MORNING)

    assert vNotification["title"] == "Nouvelle offre chez Roquette"
    assert vNotification["text"] == "Technicien de maintenance"


def test_last_week_review_is_announced_on_monday(database_file, monkeypatch):
    """Vérifie le bilan de la semaine annoncé le lundi seulement."""

    for vName in ("get_due_follow_ups", "find_hot_offers", "find_preferred_offers"):
        monkeypatch.setattr(notifications, vName, lambda *pArgs: [])

    monkeypatch.setattr(
        notifications,
        "build_progress",
        lambda *pArgs: {
            "quests": [],
            "streak": 0,
            "active_today": True,
            "season": {"key": "2026-W44", "title": "Saison 44", "summary": "310 XP"},
        },
    )

    assert pick_notification(database_file, MORNING) is None

    vNotification = pick_notification(database_file, datetime(2026, 11, 2, 10, 0))

    assert vNotification["title"] == "Bilan de la Saison 44"
    assert vNotification["text"] == "310 XP"
    assert vNotification["page"] == "progress"


def test_slow_pages_are_announced_once_a_week(database_file, monkeypatch):
    """Vérifie l'alerte des pages lentes à répétition, une fois par semaine."""

    for vName in ("get_due_follow_ups", "find_hot_offers"):
        monkeypatch.setattr(notifications, vName, lambda *pArgs: [])

    monkeypatch.setattr(
        notifications,
        "build_progress",
        lambda *pArgs: {"quests": [], "streak": 0, "active_today": True},
    )

    for _ in range(3):
        record_page_time(database_file, "bureau offers", 2.5, MORNING)

    vNotification = pick_notification(database_file, MORNING)

    assert vNotification["title"] == "1 page(s) souvent lente(s)"
    assert vNotification["text"] == "bureau offers (3 fois, jusqu'à 2.5 s)"
    assert vNotification["page"] == "logs"
    assert pick_notification(database_file, MORNING.replace(hour=11)) is None
