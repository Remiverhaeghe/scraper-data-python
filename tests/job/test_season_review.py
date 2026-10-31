"""Tests du bilan de la saison (semaine écoulée)"""

from datetime import date, timedelta

from job.season_review import build_season_review, get_medal, summarize_week

# Lundi 2 novembre 2026 : la saison résumée va du 26 octobre au 1er novembre
TODAY = date(2026, 11, 2)
MONDAY = date(2026, 10, 26)


def day(pXp, **pActions):
    """Construit une journée d'activité."""

    rDay = {"xp": pXp, "actions": pActions}

    return rDay


def test_week_is_summarized_from_monday_to_sunday():
    """Vérifie les chiffres d'une semaine ; une quête seule ne fait pas un jour actif."""

    vActivity = {
        MONDAY: day(80, applied=2, answer_right=4),
        MONDAY + timedelta(days=3): day(20, daily_quest=1),
        MONDAY + timedelta(days=6): day(45, answer_wrong=5, interview=1),
        MONDAY + timedelta(days=7): day(500, applied=9),
    }

    assert summarize_week(vActivity, MONDAY) == {
        "xp": 145,
        "active_days": 2,
        "quests": 1,
        "applications": 2,
        "answers": 9,
        "interviews": 1,
    }


def test_review_compares_with_the_week_before():
    """Vérifie la saison, l'évolution, le meilleur jour, le record et la médaille."""

    vActivity = {
        MONDAY - timedelta(days=7): day(100, applied=1),
        MONDAY + timedelta(days=1): day(60, applied=1, daily_quest=3),
        MONDAY + timedelta(days=2): day(250, applied=3, daily_quest=3, weekly_quest=1),
    }

    vReview = build_season_review(vActivity, TODAY, 22)

    assert vReview["key"] == "2026-W44" and vReview["title"] == "Saison 44"
    assert (vReview["start"], vReview["end"]) == ("2026-10-26", "2026-11-01")
    assert vReview["statistics"][0] == {
        "key": "xp",
        "label": "XP gagnée",
        "value": 310,
        "previous": 100,
        "trend": "+210",
    }
    assert vReview["statistics"][3]["trend"] == "+3"
    assert vReview["statistics"][5]["trend"] == "="
    assert vReview["best_day"] == {"day": "2026-10-28", "xp": 250}
    assert vReview["record"] is True
    assert vReview["medal"]["id"] == "bronze"
    assert vReview["summary"] == "310 XP, +210 par rapport à la semaine précédente"


def test_review_is_the_same_all_week_and_empty_without_activity():
    """Vérifie le même bilan jusqu'au dimanche, et aucun après une semaine blanche."""

    vActivity = {MONDAY: day(30, applied=1)}

    assert build_season_review(vActivity, TODAY + timedelta(days=6), 22)["key"] == (
        "2026-W44"
    )
    assert build_season_review(vActivity, TODAY + timedelta(days=7), 22) is None

    vFirst = build_season_review(vActivity, TODAY, 22)

    assert vFirst["record"] is False
    assert vFirst["summary"] == "30 XP, +30 par rapport à la semaine précédente"
    assert build_season_review(
        {MONDAY: day(30), MONDAY - timedelta(days=7): day(30)}, TODAY, 22
    )["summary"] == ("30 XP, autant que la semaine précédente")


def test_medal_follows_the_share_of_quests():
    """Vérifie l'or, l'argent, le bronze et l'absence de médaille."""

    assert get_medal(17, 22)["id"] == "or"
    assert get_medal(9, 22)["id"] == "argent"
    assert get_medal(4, 22) == {
        "id": "bronze",
        "label": "Médaille de bronze : 4 quêtes sur 22",
        "color": "#B45309",
    }
    assert get_medal(2, 22) is None
    assert get_medal(0, 0) is None
