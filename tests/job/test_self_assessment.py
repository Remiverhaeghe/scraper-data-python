"""Tests de la grille d'auto-évaluation des compétences"""

import pytest

from job.preparation import match_profile
from job.profile import EMPTY_PROFILE, build_profile, load_profile, save_profile
from job.quiz import load_quiz
from job.self_assessment import (
    GRID_SKILLS,
    build_grid,
    find_weak_themes,
    get_assessed_skills,
    save_skill_levels,
)
from storage.database import initialize_database


@pytest.fixture(name="database_file")
def fixture_database_file(tmp_path):
    """Crée une base vide."""

    rDatabaseFile = tmp_path / "scraper.db"
    initialize_database(rDatabaseFile)

    return rDatabaseFile


def test_grid_adds_profile_skills_without_duplicates():
    """Vérifie la grille : compétences de départ, puis celles du profil."""

    vGrid = build_grid(
        {**EMPTY_PROFILE, "skills": ["java", "Kafka"], "skill_levels": {"Kafka": 6}}
    )

    assert [vSkill for vSkill, _ in vGrid] == [*GRID_SKILLS, "Kafka"]
    assert dict(vGrid)["Kafka"] == 6


def test_levels_are_saved_kept_by_the_profile_form_and_checked(database_file):
    """Vérifie l'enregistrement, la conservation au profil suivant et le refus."""

    save_skill_levels(database_file, {"Java": 7, "PHP": 0, "Android": 3})

    assert load_profile(database_file)["skill_levels"] == {"Java": 7, "Android": 3}

    save_profile(database_file, build_profile("Rémi", "", "Python", "", ""))

    assert load_profile(database_file)["skill_levels"] == {"Java": 7, "Android": 3}

    with pytest.raises(ValueError, match="Niveau de 0 à 10"):
        save_skill_levels(database_file, {"Java": 11})


def test_assessed_skills_count_in_the_match_and_weak_ones_point_to_themes():
    """Vérifie l'effet des niveaux : score des offres et thèmes à renforcer."""

    vProfile = {
        **EMPTY_PROFILE,
        "skill_levels": {"Java": 7, "Android": 2, "PHP": 4, "SQL": 1},
    }

    assert get_assessed_skills(vProfile) == ["Java"]
    # Java noté 7 sur 8 : 0,875 rapporté au plancher de 3 compétences
    assert match_profile(vProfile, ["Java", "Docker"])["score"] == 29

    vThemes = find_weak_themes(vProfile, load_quiz())

    assert [(vTheme["key"], vTheme["level"]) for vTheme in vThemes][:2] == [
        ("sql", 1),
        ("entretien_android", 2),
    ]
    assert "entretien_web" in [vTheme["key"] for vTheme in vThemes]
