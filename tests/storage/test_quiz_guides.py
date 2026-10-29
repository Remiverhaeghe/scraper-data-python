"""Tests des guides pratiques : livrés avec l'application ou importés"""

from datetime import datetime

from job.quiz import load_quiz
from job.quiz_generation import load_catalog
from storage.database import initialize_database
from storage.quiz_questions import (
    get_quiz_guide,
    get_quiz_guides,
    load_shipped_guides,
    save_quiz_guides,
)


def test_shipped_guide_is_listed_then_replaced_by_an_imported_one(tmp_path):
    """Vérifie le guide livré, puis la priorité d'un guide importé du même nom."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)

    vLean = get_quiz_guide(vDatabaseFile, "lean")

    assert vLean["title"] == "Lean et amélioration continue"
    assert "Takt time" in vLean["content"]
    assert {"name": "lean", "theme": "lean", "title": vLean["title"]} in (
        get_quiz_guides(vDatabaseFile)
    )

    save_quiz_guides(
        vDatabaseFile,
        [("lean", "lean", "Lean importé", "# Lean importé")],
        datetime(2026, 10, 30),
    )

    assert get_quiz_guide(vDatabaseFile, "lean")["title"] == "Lean importé"
    assert [vGuide["name"] for vGuide in get_quiz_guides(vDatabaseFile)].count(
        "lean"
    ) == 1


def test_every_shipped_guide_belongs_to_a_theme():
    """Vérifie que chaque guide livré porte le nom d'un thème connu."""

    vThemes = set(load_quiz()) | {vTheme["id"] for vTheme in load_catalog()}

    assert load_shipped_guides()
    assert set(load_shipped_guides()) <= vThemes
