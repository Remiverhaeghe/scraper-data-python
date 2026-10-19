"""Tests des réponses STAR aux questions comportementales"""

import pytest

from job.preparation import prepare_application
from job.profile import build_profile
from job.star_answers import (
    MAX_FIELD_LENGTH,
    load_star_answers,
    save_star_answer,
    select_star_answers,
    suggest_star_answer,
)
from storage.database import initialize_database
from storage.settings_repository import save_setting_values

PROFILE = build_profile(
    "",
    "",
    "Java, Python",
    "Développeur backend | Java, Spring | Réduit de 40 % le temps de réponse\n"
    "Data engineer | Python | Fiabilisé les flux nocturnes",
    "",
)


@pytest.fixture
def database_file(tmp_path):
    """Crée une base vide."""

    rDatabaseFile = tmp_path / "scraper.db"

    initialize_database(rDatabaseFile)

    return rDatabaseFile


def test_save_and_remove_star_answer(database_file):
    """Vérifie l'enregistrement, le nettoyage des champs et le retrait d'une réponse."""

    save_star_answer(
        database_file,
        "reussite",
        "Data engineer",
        {"situation": " Flux en échec ", "result": "Zéro incident"},
    )

    assert load_star_answers(database_file) == {
        "reussite": {
            "experience": "Data engineer",
            "situation": "Flux en échec",
            "task": "",
            "action": "",
            "result": "Zéro incident",
        }
    }

    save_star_answer(database_file, "reussite", "", {})

    assert load_star_answers(database_file) == {}


@pytest.mark.parametrize(
    "pKey, pFields, pMessage",
    [
        ("inconnue", {"action": "x"}, "inconnue"),
        ("echec", {"action": "x" * (MAX_FIELD_LENGTH + 1)}, "trop longue"),
    ],
)
def test_save_star_answer_rejects_invalid_input(database_file, pKey, pFields, pMessage):
    """Vérifie le refus d'une question inconnue ou d'une partie trop longue."""

    with pytest.raises(ValueError, match=pMessage):
        save_star_answer(database_file, pKey, "", pFields)


def test_unreadable_star_answers_are_ignored(database_file):
    """Vérifie qu'un réglage illisible donne des réponses vides."""

    save_setting_values(database_file, {"star_answers": "pas du json"})

    assert load_star_answers(database_file) == {}


def test_suggest_star_answer_uses_the_achievement():
    """Vérifie le pré-remplissage à partir de l'expérience choisie."""

    vAnswer = suggest_star_answer(PROFILE, "Data engineer")

    assert vAnswer["situation"] == "Data engineer"
    assert vAnswer["result"] == "Fiabilisé les flux nocturnes"
    assert suggest_star_answer(PROFILE, "")["result"] == ""


def test_star_answers_matching_the_offer_come_first():
    """Vérifie l'ordre des réponses et leur présence dans la préparation."""

    vAnswers = {
        "reussite": {"experience": "Développeur backend", "result": "Plus rapide"},
        "echec": {"experience": "Data engineer", "action": "Revu les alertes"},
    }

    vSelected = select_star_answers(vAnswers, PROFILE, ["Python"])

    assert [vAnswer["experience"] for vAnswer in vSelected] == [
        "Data engineer",
        "Développeur backend",
    ]
    assert vSelected[0]["skills"] == ["python"]
    assert vSelected[1]["text"] == "Résultat : Plus rapide"

    vPreparation = prepare_application(
        PROFILE, {"title": "Développeur Python", "description": ""}, vAnswers
    )

    assert vPreparation["interview"]["star"][0]["experience"] == "Data engineer"
