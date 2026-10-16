"""Tests de la révision ciblée sur une offre et de son examen blanc"""

import random
from datetime import datetime

import pytest

from job.interview_revision import (
    build_offer_revision,
    describe_offer_exam,
    find_offer_themes,
    start_offer_exam,
)
from job.quiz import load_quiz
from storage.database import initialize_database

NOW = datetime(2026, 10, 16, 10, 0)

OFFER = {
    "source": "adzuna",
    "source_id": "42",
    "title": "Développeur Python",
    "company": "Entreprise A",
    "description": "API FastAPI, base PostgreSQL, déploiement Docker.",
}


@pytest.fixture
def database_file(tmp_path):
    """Crée une base vide."""

    rDatabaseFile = tmp_path / "scraper.db"

    initialize_database(rDatabaseFile)

    return rDatabaseFile


def test_find_offer_themes():
    """Vérifie les thèmes retenus et ignore une offre aux mots trop génériques."""

    vQuiz = load_quiz()

    assert find_offer_themes(vQuiz, OFFER) == {
        "docker": ["Docker"],
        "python": ["Python", "FastAPI"],
        "sql": ["PostgreSQL"],
    }
    assert (
        find_offer_themes(
            vQuiz,
            {"title": "Technicien support", "description": "Maintenance et HTTP."},
        )
        == {}
    )


def test_build_offer_revision_orders_weakest_first(database_file):
    """Vérifie que les thèmes les moins maîtrisés viennent en premier."""

    vRevision = build_offer_revision(database_file, load_quiz(), OFFER)

    assert [vTheme["key"] for vTheme in vRevision["themes"]] == [
        "docker",
        "python",
        "sql",
    ]
    assert vRevision["themes"][1]["matched"] == ["Python", "FastAPI"]
    assert vRevision["exam_count"] == 20


def test_start_offer_exam(database_file):
    """Vérifie que l'examen blanc ne tire que dans les thèmes de l'offre."""

    vQuiz = load_quiz()
    vExam = start_offer_exam(database_file, vQuiz, OFFER, NOW, random.Random(1))
    vAllowed = {
        vQuestion["id"]
        for vKey in ("docker", "python", "sql")
        for vQuestion in vQuiz[vKey]["questions"]
    }

    assert set(vExam["ids"]) <= vAllowed
    assert vExam["title"] == "Entretien : Développeur Python chez Entreprise A"
    assert describe_offer_exam({}) == "Entretien : offre sans titre"

    with pytest.raises(ValueError, match="Aucun thème"):
        start_offer_exam(database_file, vQuiz, {"title": "Comptable"}, NOW)
