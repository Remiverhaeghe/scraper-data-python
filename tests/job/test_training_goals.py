"""Tests des formations et certifications visées"""

from datetime import date

import pytest

from job.certifications import load_owned, save_owned
from job.training_goals import (
    MAX_GOALS,
    build_goals_overview,
    clean_goal,
    delete_goal,
    load_goals,
    parse_skills,
    save_goal,
)
from storage.database import initialize_database
from storage.settings_repository import save_json_setting

TODAY = date(2026, 11, 19)
KNOWN = {"python": "Python", "sql": "SQL", "docker": "Docker", "java": "Java"}


@pytest.fixture
def database_file(tmp_path):
    """Retourne une base vide."""

    rDatabaseFile = tmp_path / "scraper.db"
    initialize_database(rDatabaseFile)

    return rDatabaseFile


def test_parse_skills_uses_catalog_spelling_without_duplicates():
    """Vérifie la saisie des compétences : écriture du catalogue, doublons écartés."""

    assert parse_skills("python, SQL , Python,, Gestion de projet", KNOWN) == [
        "Python",
        "SQL",
        "Gestion de projet",
    ]
    assert parse_skills(None, KNOWN) == []
    assert len(parse_skills(",".join(f"c{vIndex}" for vIndex in range(20)), {})) == 10


@pytest.mark.parametrize(
    ("pForm", "pMessage"),
    [
        ({}, "Indiquez la formation"),
        ({"certification": "inconnue"}, "Certification inconnue"),
        ({"title": "Cours", "status": "fini"}, "État inconnu"),
        ({"title": "Cours", "target": "demain"}, "Date visée invalide"),
        ({"title": "Cours", "link": "javascript:alert(1)"}, "https://"),
    ],
)
def test_clean_goal_rejects_invalid_input(pForm, pMessage):
    """Vérifie le refus d'une saisie incomplète ou dangereuse."""

    with pytest.raises(ValueError, match=pMessage):
        clean_goal(pForm, KNOWN)


def test_clean_goal_takes_catalog_label():
    """Vérifie qu'une certification du catalogue prend son libellé par défaut."""

    vGoal = clean_goal({"certification": "sst", "skills": "secourisme"}, KNOWN)

    assert vGoal["title"] == "Sauveteur secouriste du travail (SST)"
    assert vGoal["status"] == "planned"
    assert vGoal["skills"] == ["secourisme"]


def test_goal_is_added_updated_then_deleted(database_file):
    """Vérifie l'ajout, la modification et le retrait d'un objectif."""

    vId = save_goal(
        database_file,
        {"title": "Développeur web (titre pro fictif)", "skills": "python, sql"},
        KNOWN,
        TODAY,
    )
    save_goal(
        database_file,
        {"id": vId, "title": "Développeur web", "status": "in_progress"},
        KNOWN,
        TODAY,
    )

    vGoals = load_goals(database_file)

    assert len(vGoals) == 1
    assert vGoals[0]["id"] == vId
    assert vGoals[0]["title"] == "Développeur web"
    assert vGoals[0]["status"] == "in_progress"
    assert vGoals[0]["skills"] == []

    assert delete_goal(database_file, vId) is True
    assert delete_goal(database_file, vId) is False
    assert load_goals(database_file) == []


def test_load_goals_skips_malformed_entries(database_file):
    """Vérifie que les objectifs illisibles sont ignorés."""

    save_json_setting(
        database_file,
        "training_goals",
        [{"id": "a", "title": "Cours"}, {"id": "b"}, "texte", {"title": "Sans id"}],
    )

    assert [vGoal["id"] for vGoal in load_goals(database_file)] == ["a"]


def test_goal_count_is_limited(database_file):
    """Vérifie le nombre maximal d'objectifs."""

    save_json_setting(
        database_file,
        "training_goals",
        [{"id": str(vIndex), "title": "Cours"} for vIndex in range(MAX_GOALS)],
    )

    with pytest.raises(ValueError, match="objectifs au plus"):
        save_goal(database_file, {"title": "Un de trop"}, KNOWN, TODAY)


def test_obtained_certification_is_ticked_once(database_file):
    """Vérifie qu'une certification obtenue est cochée sans écraser sa date."""

    save_goal(database_file, {"certification": "sst", "status": "done"}, KNOWN, TODAY)

    assert load_owned(database_file) == {"sst": "2026-11-19"}

    save_owned(database_file, "sst", date(2025, 3, 1))
    save_goal(database_file, {"certification": "sst", "status": "done"}, KNOWN, TODAY)

    assert load_owned(database_file) == {"sst": "2025-03-01"}

    # Une formation libre obtenue ne touche pas aux certifications.
    save_goal(database_file, {"title": "Cours SQL", "status": "done"}, KNOWN, TODAY)

    assert load_owned(database_file) == {"sst": "2025-03-01"}


def test_overview_links_goals_to_offers():
    """Vérifie les offres servies par chaque objectif, le retard et les manques."""

    vOffers = [
        {"title": "Développeur Python", "skills": '["Python", "SQL"]'},
        {"title": "Data analyst", "skills": '["SQL"]', "description": "SST apprécié"},
        {"title": "Dev Java", "skills": '["Java", "Docker"]'},
        {"title": "Ops", "skills": '["Docker"]'},
    ]
    vGoals = [
        {
            "id": "a",
            "title": "Cours Python",
            "status": "in_progress",
            "target": "2026-10-01",
            "skills": ["Python", "SQL"],
        },
        {
            "id": "b",
            "title": "SST",
            "certification": "sst",
            "status": "planned",
            "target": "2026-12-01",
            "skills": [],
        },
        {"id": "c", "title": "Java", "status": "dropped", "skills": ["java"]},
    ]

    vOverview = build_goals_overview(vGoals, vOffers, KNOWN, TODAY)
    vRows = {vRow["id"]: vRow for vRow in vOverview["rows"]}

    assert vOverview["offers"] == 4
    assert vRows["a"]["skill_offers"] == 2
    assert vRows["a"]["skill_counts"] == [("Python", 1), ("SQL", 2)]
    assert vRows["a"]["late"] is True
    assert vRows["a"]["certification_offers"] is None
    assert vRows["b"]["certification_offers"] == 1
    assert vRows["b"]["late"] is False
    assert vRows["c"]["status_label"] == ("Abandonnée", "muted")
    assert vOverview["counts"] == {
        "planned": 1,
        "in_progress": 1,
        "done": 0,
        "dropped": 1,
    }
    # Java a un objectif abandonné : il compte de nouveau parmi les manques.
    assert vOverview["uncovered"] == [("Docker", 2), ("Java", 1)]
