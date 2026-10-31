"""Tests de la mascotte : humeur et phrase selon la progression, dessin"""

from datetime import datetime

import pytest

from job.mascot import MOODS, PHRASES, build_mascot, draw_mascot

NOW = datetime(2026, 10, 31, 9, 0)


def make_progress(**pValues):
    """Retourne une progression de base, modifiée par pValues."""

    rProgress = {
        "xp": 120,
        "level": 2,
        "level_before_today": 2,
        "title": "Apprenti",
        "streak": 1,
        "history": [{"day": "2026-10-31", "xp": 10}],
        "quests": [],
        "achievements": [],
        **pValues,
    }

    return rProgress


QUEST = {
    "weekly": False,
    "label": "Répondre à 10 questions",
    "progress": 7,
    "target": 10,
}


@pytest.mark.parametrize(
    "pValues, pSituation, pMood",
    [
        ({"xp": 0, "history": []}, "welcome", "happy"),
        ({"history": [{"day": "2026-10-27", "xp": 5}]}, "asleep", "asleep"),
        ({"history": [{"day": "2026-10-29", "xp": 5}]}, "morning", "happy"),
        ({"level_before_today": 1}, "level", "proud"),
        (
            {"achievements": [{"title": "Sans faute", "unlocked_on": "2026-10-31"}]},
            "trophy",
            "proud",
        ),
        ({"quests": [{**QUEST, "done": True}]}, "quests_done", "proud"),
        ({"quests": [{**QUEST, "done": False}]}, "quest", "focused"),
        ({"streak": 4}, "streak", "happy"),
    ],
)
def test_situation_follows_the_progress(pValues, pSituation, pMood):
    """Vérifie l'humeur et la situation choisies, par ordre de priorité."""

    vMascot = build_mascot(make_progress(**pValues), NOW)

    assert (vMascot["situation"], vMascot["mood"]) == (pSituation, pMood)
    assert "{" not in vMascot["text"]


def test_quest_phrase_names_the_closest_quest():
    """Vérifie la phrase d'une quête en cours, avec ce qui reste à faire."""

    vText = build_mascot(make_progress(quests=[{**QUEST, "done": False}]), NOW)["text"]

    assert "Répondre à 10 questions" in vText and "3" in vText


@pytest.mark.parametrize(
    "pHour, pSituation", [(8, "morning"), (14, "afternoon"), (21, "evening")]
)
def test_greeting_follows_the_time_of_day(pHour, pSituation):
    """Vérifie le salut du matin, de l'après-midi et du soir."""

    vMascot = build_mascot(make_progress(), NOW.replace(hour=pHour))

    assert vMascot["situation"] == pSituation
    assert vMascot["text"] in PHRASES[pSituation]


def test_same_phrase_all_day_and_every_mood_drawn():
    """Vérifie une phrase stable dans la journée et un dessin par humeur."""

    vProgress = make_progress(streak=5)

    assert (
        build_mascot(vProgress, NOW)["text"]
        == build_mascot(vProgress, NOW.replace(hour=11))["text"]
    )
    assert len({draw_mascot(vMood) for vMood in MOODS}) == len(MOODS)
    assert draw_mascot("inconnue") == draw_mascot("happy")
