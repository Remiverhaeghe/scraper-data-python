"""Tests de la carte du bilan de la saison"""

from gui.season_card import SeasonCard, get_trend_color
from gui.theme import COLORS

REVIEW = {
    "key": "2026-W44",
    "title": "Saison 44",
    "start": "2026-10-26",
    "end": "2026-11-01",
    "statistics": [
        {
            "key": "xp",
            "label": "XP gagnée",
            "value": 310,
            "previous": 100,
            "trend": "+210",
        },
        {
            "key": "applications",
            "label": "Candidatures",
            "value": 1,
            "previous": 3,
            "trend": "-2",
        },
    ],
    "best_day": {"day": "2026-10-28", "xp": 250},
    "medal": {
        "id": "or",
        "label": "Médaille d'or : 17 quêtes sur 22",
        "color": "#EAB308",
    },
    "record": True,
    "summary": "310 XP, +210 par rapport à la semaine précédente",
}


def test_card_shows_the_review_then_an_empty_week(qt_application):
    """Vérifie le bilan affiché, puis le message d'une semaine sans activité."""

    vCard = SeasonCard()
    vCard.set_review(REVIEW)

    assert vCard.title_label.text() == (
        "Saison 44 · du 26/10 au 01/11 · record des huit dernières semaines"
    )
    assert "Médaille d'or" in vCard.medal_label.text()
    assert not vCard.medal_icon.pixmap().isNull()
    assert vCard.statistics_grid.count() == 2
    assert vCard.best_day_label.text() == "Meilleur jour : le 28/10, 250 XP"

    vCard.set_review({**REVIEW, "medal": None, "record": False})

    assert vCard.medal_label.isHidden()
    assert "record" not in vCard.title_label.text()

    vCard.set_review(None)

    assert vCard.title_label.text() == "Pas de bilan cette semaine"
    assert vCard.statistics_grid.count() == 0
    assert vCard.best_day_label.isHidden()


def test_trend_color_follows_the_evolution():
    """Vérifie le vert en hausse, le rouge en baisse et le gris à égalité."""

    assert get_trend_color(REVIEW["statistics"][0]) == COLORS["success"]
    assert get_trend_color(REVIEW["statistics"][1]) == COLORS["danger"]
    assert get_trend_color({"value": 2, "previous": 2}) == COLORS["muted"]
