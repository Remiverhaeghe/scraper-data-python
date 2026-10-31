"""Tests des récompenses cosmétiques : déblocage par niveau, choix, retombée"""

import pytest

from job.cosmetics import (
    ACCENTS,
    FRAMES,
    build_cosmetics_view,
    choose_cosmetic,
    get_accent_colors,
    load_cosmetics,
    set_sounds,
)
from storage.database import initialize_database


@pytest.fixture
def database_file(tmp_path):
    """Fournit une base vide."""

    rDatabaseFile = tmp_path / "scraper.db"
    initialize_database(rDatabaseFile)

    return rDatabaseFile


def test_rewards_unlock_with_levels(database_file):
    """Vérifie les récompenses débloquées au niveau 4 et les valeurs de départ."""

    vView = build_cosmetics_view(database_file, 4)

    assert (vView["accent"], vView["frame"], vView["sounds"]) == ("bleu", "aucun", True)
    assert [vItem["unlocked"] for vItem in vView["accents"]] == [
        vLevel <= 4 for _, vLevel, _, _ in ACCENTS.values()
    ]
    assert [vItem["id"] for vItem in vView["frames"] if vItem["unlocked"]] == [
        "aucun",
        "bronze",
    ]


def test_choice_is_saved_refused_when_locked_and_falls_back(database_file):
    """Vérifie un choix enregistré, un choix verrouillé refusé et la retombée sous le niveau."""

    choose_cosmetic(database_file, "accent", "violet", 4)
    choose_cosmetic(database_file, "frame", "bronze", 4)
    set_sounds(database_file, False)

    vView = build_cosmetics_view(database_file, 4)

    assert (vView["accent"], vView["frame_color"], vView["sounds"]) == (
        "violet",
        FRAMES["bronze"][2],
        False,
    )

    with pytest.raises(ValueError, match="niveau 10"):
        choose_cosmetic(database_file, "accent", "or", 4)

    for vKind, vId in (("accent", "inconnu"), ("couleur", "vert")):
        with pytest.raises(ValueError, match="inconnue"):
            choose_cosmetic(database_file, vKind, vId, 10)

    assert build_cosmetics_view(database_file, 2)["accent"] == "bleu"
    assert load_cosmetics(database_file)["accent"] == "violet"


def test_accent_colors_replace_the_theme_tints():
    """Vérifie les teintes d'un accent en clair et en sombre, et le bleu d'origine."""

    assert get_accent_colors("vert", "light")["primary"] == "#15803D"
    assert get_accent_colors("vert", "dark")["primary"] == "#4ADE80"
    assert get_accent_colors("bleu", "light") == {} == get_accent_colors(None, "dark")
    assert all(set(vLight) == set(vDark) for _, _, vLight, vDark in ACCENTS.values())
