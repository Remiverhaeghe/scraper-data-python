"""Tests de la progression : points, niveaux, série et quêtes"""

from datetime import date, datetime, timedelta

import pytest

from job.progress import (
    build_progress,
    compute_streak,
    describe_level,
    draw_daily_quests,
    get_total_xp,
)
from storage.database import connect_database, initialize_database
from storage.job_applications import save_application

NOW = datetime(2026, 10, 29, 18, 0)
TODAY = NOW.date()


@pytest.fixture
def database_file(tmp_path):
    """Crée une base vide."""

    rDatabaseFile = tmp_path / "scraper.db"
    initialize_database(rDatabaseFile)

    return rDatabaseFile


def answer(pDatabaseFile, pCount, pCorrect=True, pDay=TODAY):
    """Enregistre des réponses de révision à une date donnée."""

    vConnection = connect_database(pDatabaseFile)

    try:
        vConnection.executemany(
            "INSERT INTO quiz_answer (question_id, theme, correct, answered_at)"
            " VALUES (?, 'sql', ?, ?)",
            [
                (f"q{vIndex}", int(pCorrect), f"{pDay}T10:00")
                for vIndex in range(pCount)
            ],
        )
        vConnection.commit()

    finally:
        vConnection.close()


@pytest.mark.parametrize(
    ("pXp", "pLevel", "pTitle", "pInLevel"),
    [
        (0, 1, "Apprenti", 0),
        (99, 1, "Apprenti", 99),
        (100, 2, "Apprenti confirmé", 0),
        (350, 3, "Technicien", 50),
        (4500, 10, "Légende", 0),
        (5500, 11, "Légende 2", 0),
    ],
)
def test_levels_grow_with_points(pXp, pLevel, pTitle, pInLevel):
    """Vérifie les seuils des niveaux, de plus en plus espacés, et leurs titres."""

    vLevel = describe_level(pXp)

    assert (vLevel["level"], vLevel["title"], vLevel["xp_in_level"]) == (
        pLevel,
        pTitle,
        pInLevel,
    )


def test_streak_forgives_one_missed_day_per_week():
    """Vérifie la série : commencée hier, joker d'un jour par semaine, pas deux."""

    vDays = [TODAY - timedelta(days=vOffset) for vOffset in (1, 2, 4, 5, 6)]

    assert compute_streak(vDays, TODAY) == (5, 5)
    assert compute_streak([TODAY - timedelta(days=3)], TODAY) == (0, 1)
    assert compute_streak([], TODAY) == (0, 0)


def test_points_come_from_existing_activity(database_file):
    """Vérifie les points des révisions et des candidatures, sans saisie de plus."""

    answer(database_file, 3)
    answer(database_file, 2, pCorrect=False)
    save_application(database_file, "lever", "1", "APPLIED", pNow=NOW)

    assert get_total_xp(database_file) == 3 * 5 + 2 * 2 + 30


def test_quests_are_kept_for_the_day_and_rewarded_once(database_file):
    """Vérifie les quêtes figées pour la journée, puis leurs points comptés une fois."""

    vFirst = build_progress(database_file, NOW)
    answer(database_file, 10)
    vSecond = build_progress(database_file, NOW + timedelta(hours=1))
    vThird = build_progress(database_file, NOW + timedelta(hours=2))

    vRevise = next(vQuest for vQuest in vSecond["quests"] if vQuest["id"] == "revise")

    assert [vQuest["id"] for vQuest in vFirst["quests"]] == [
        vQuest["id"] for vQuest in vSecond["quests"]
    ]
    assert vRevise["done"] and vRevise["progress"] == 10
    assert vSecond["xp"] == 10 * 5 + 20
    assert vThird["xp"] == vSecond["xp"]
    assert vSecond["streak"] == 1 and vSecond["active_today"]


def test_urgent_quests_come_first():
    """Vérifie la relance due et l'entretien proche en tête, sans offre à postuler."""

    vQuests = draw_daily_quests(
        {"follow_up_due": True, "interview_soon": True, "new_offers": False},
        date(2026, 10, 29),
    )

    assert vQuests[:2] == ["follow_up", "exam"]
    assert "revise" in vQuests
    assert "apply" not in vQuests
