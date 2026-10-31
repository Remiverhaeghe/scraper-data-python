"""Cas des simulations communs au PC et au téléphone, et leur intégration"""

import json

import pytest
from datetime import datetime

from job.code_puzzles import get_answer
from job.mobile_labs import build_labs_package, sync_lab_results
from job.troubleshooting import load_results
from storage.database import initialize_database
from tools.lab_cases import FIXTURE_FILE, build_cases


def test_shared_cases_are_up_to_date():
    """Vérifie le fichier commun : à régénérer par python -m tools.lab_cases."""

    vCases = json.loads(json.dumps(build_cases()))

    assert json.loads(FIXTURE_FILE.read_text(encoding="utf-8")) == vCases
    assert {vCase["expected"]["score"] for vCase in vCases["troubleshooting"]} >= {
        12,
        38,
    }


def test_phone_results_are_replayed_and_counted_once(tmp_path):
    """Vérifie la partie rejouée par le PC, l'envoi répété ignoré et les refus."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    vScenario = build_labs_package(vDatabaseFile)["troubleshooting"]["scenarios"][0]
    vRight = next(vCause for vCause in vScenario["causes"] if vCause.get("right"))
    vResult = {
        "id": "partie-1",
        "lab": "troubleshooting",
        "scenario": vScenario["id"],
        "actions": [f"repair:{vRight['id']}"],
        "finished_at": "2026-10-30T09:00:00",
        "score": 100,
    }

    vReport = sync_lab_results(
        vDatabaseFile,
        [
            vResult,
            {**vResult, "id": "partie-2", "actions": []},
            {**vResult, "id": "partie-3", "scenario": "inconnu"},
        ],
    )

    assert vReport["saved"] == 1
    assert [vItem["reason"] for vItem in vReport["rejected"]] == [
        "panne non résolue",
        "simulation ou scénario inconnu",
    ]
    assert load_results(vDatabaseFile)[0]["score"] == 50
    assert load_results(vDatabaseFile)[0]["finished_at"] == datetime(
        2026, 10, 30, 9, 0
    ).isoformat(timespec="seconds")
    assert sync_lab_results(vDatabaseFile, [vResult])["saved"] == 0


def test_phone_ladder_program_is_checked_again(tmp_path):
    """Vérifie un programme réussi compté une fois, et un programme faux refusé."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    vLevel = build_labs_package(vDatabaseFile)["ladder"]["levels"][0]
    vResult = {
        "id": "automate-1",
        "lab": "ladder",
        "level": vLevel["id"],
        "program": vLevel["solution"],
        "finished_at": "2026-10-30T09:00:00",
    }

    vReport = sync_lab_results(
        vDatabaseFile,
        [
            vResult,
            {**vResult, "id": "automate-2"},
            {**vResult, "id": "automate-3", "program": vLevel["starter"]},
        ],
    )

    assert (vReport["saved"], vReport["xp"]) == (2, 25)
    assert vReport["rejected"][0]["reason"] == "niveau non réussi"
    assert build_labs_package(vDatabaseFile)["ladder"]["passed"] == [vLevel["id"]]


def test_phone_git_history_is_replayed(tmp_path):
    """Vérifie des commandes Git qui atteignent l'objectif, et un historique incomplet refusé."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    vResult = {
        "id": "git-1",
        "lab": "git",
        "level": "premiers-commits",
        "history": ["git commit", "git commit"],
        "finished_at": "2026-10-30T09:00:00",
    }

    vReport = sync_lab_results(
        vDatabaseFile,
        [vResult, {**vResult, "id": "git-2", "history": ["git commit"]}],
    )

    assert (vReport["saved"], vReport["xp"]) == (1, 25)
    assert vReport["rejected"][0]["reason"] == "niveau non réussi"
    assert build_labs_package(vDatabaseFile)["git"]["best"] == {"premiers-commits": 2}


def test_phone_devops_steps_are_replayed(tmp_path):
    """Vérifie des étapes Docker qui atteignent l'objectif, et des étapes insuffisantes refusées."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    vLevel = next(
        vItem
        for vItem in build_labs_package(vDatabaseFile)["devops"]["levels"]
        if vItem["id"] == "docker-port-pris"
    )
    vSteps = [
        {"file": vLevel["solution"], "command": vCommand}
        for vCommand in vLevel["commands"]
    ]
    vResult = {
        "id": "devops-1",
        "lab": "devops",
        "level": vLevel["id"],
        "steps": vSteps,
        "finished_at": "2026-10-30T09:00:00",
    }

    vReport = sync_lab_results(
        vDatabaseFile,
        [vResult, {**vResult, "id": "devops-2", "steps": vSteps[:2]}],
    )

    assert (vReport["saved"], vReport["xp"]) == (1, 20)
    assert vReport["rejected"][0]["reason"] == "niveau non réussi"
    assert build_labs_package(vDatabaseFile)["devops"]["passed"] == [vLevel["id"]]


def test_phone_sql_query_is_run_again(tmp_path):
    """Vérifie une requête SQL Server réussie comptée une fois, et une requête fausse refusée."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    vResult = {
        "id": "sql-1",
        "lab": "sql",
        "level": "plus-cheres",
        "dialect": "sqlserver",
        "query": "SELECT TOP 3 id, cout FROM intervention ORDER BY cout DESC",
        "finished_at": "2026-10-30T09:00:00",
    }

    vReport = sync_lab_results(
        vDatabaseFile,
        [vResult, {**vResult, "id": "sql-2", "dialect": "mysql"}],
    )

    assert (vReport["saved"], vReport["xp"]) == (1, 15)
    assert vReport["rejected"][0]["reason"] == "niveau non réussi"
    assert "plus-cheres" in build_labs_package(vDatabaseFile)["sql"]["passed"]


def test_phone_circuit_is_simulated_again(tmp_path):
    """Vérifie un montage réussi compté une fois, un montage incomplet et un schéma forgé refusés."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    vLevel = next(
        vLevel
        for vLevel in build_labs_package(vDatabaseFile)["circuit"]["levels"]
        if vLevel["id"] == "led-resistance"
    )
    vSchema = {
        "components": vLevel["solution_components"],
        "wires": vLevel["solution_wires"],
    }
    vResult = {
        "id": "circuit-1",
        "lab": "circuit",
        "level": "led-resistance",
        "schema": vSchema,
        "values": {"resistance": 470.0, "pile": 48.0},
        "finished_at": "2026-10-31T09:00:00",
    }

    vReport = sync_lab_results(
        vDatabaseFile,
        [
            vResult,
            {**vResult, "id": "circuit-2", "values": {"resistance": 1.0}},
            {**vResult, "id": "circuit-3", "schema": {"components": "forgé"}},
        ],
    )

    assert (vReport["saved"], vReport["xp"]) == (1, 20)
    assert [vItem["reason"] for vItem in vReport["rejected"]] == [
        "niveau non réussi",
        "Schéma illisible.",
    ]
    assert "led-resistance" in build_labs_package(vDatabaseFile)["circuit"]["passed"]


def test_phone_puzzle_series_is_graded_again(tmp_path):
    """Vérifie une série de puzzles du téléphone recorrigée, avec ses points, et une série incomplète refusée."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    vPuzzles = build_labs_package(vDatabaseFile)["puzzles"]["puzzles"][:10]
    vResult = {
        "id": "puzzles-1",
        "lab": "puzzles",
        "answers": [
            {"id": vPuzzle["id"], "response": get_answer(vPuzzle)}
            for vPuzzle in vPuzzles
        ],
        "finished_at": "2026-10-31T10:00:00",
    }

    vReport = sync_lab_results(
        vDatabaseFile,
        [vResult, {**vResult, "id": "puzzles-2", "answers": vResult["answers"][:9]}],
    )

    assert (vReport["saved"], vReport["xp"]) == (1, 30)
    assert vReport["rejected"][0]["reason"] == "série incomplète"
    assert build_labs_package(vDatabaseFile)["puzzles"]["level"] == 2


ENVELOPE = {"id": "partie-x", "finished_at": "2026-10-31T10:00:00"}


@pytest.mark.parametrize(
    "pItem, pReason",
    [
        ("illisible", "partie illisible"),
        ({"lab": "sql"}, "identifiant de partie manquant"),
        ({"id": "x", "finished_at": "hier"}, "date de fin illisible"),
        ({**ENVELOPE, "lab": "inconnu"}, "simulation ou scénario inconnu"),
        ({**ENVELOPE, "lab": "troubleshooting", "actions": "x"}, "actions illisibles"),
        (
            {**ENVELOPE, "lab": "troubleshooting", "scenario": "x", "actions": []},
            "simulation ou scénario inconnu",
        ),
        (
            {
                **ENVELOPE,
                "lab": "troubleshooting",
                "scenario": "differentiel",
                "actions": [],
            },
            "panne non résolue",
        ),
        ({**ENVELOPE, "lab": "ladder", "level": "x"}, "simulation ou niveau inconnu"),
        (
            {**ENVELOPE, "lab": "ladder", "level": "marche-arret", "program": 3},
            "programme illisible",
        ),
        (
            {**ENVELOPE, "lab": "ladder", "level": "marche-arret", "program": ""},
            "niveau non réussi",
        ),
        ({**ENVELOPE, "lab": "git", "level": "x"}, "simulation ou niveau inconnu"),
        (
            {**ENVELOPE, "lab": "git", "level": "premiers-commits", "history": [1]},
            "commandes illisibles",
        ),
        (
            {**ENVELOPE, "lab": "git", "level": "premiers-commits", "history": []},
            "niveau non réussi",
        ),
        ({**ENVELOPE, "lab": "devops", "level": "x"}, "simulation ou niveau inconnu"),
        (
            {**ENVELOPE, "lab": "devops", "level": "docker-port-pris", "steps": [{}]},
            "étapes illisibles",
        ),
        (
            {
                **ENVELOPE,
                "lab": "devops",
                "level": "docker-port-pris",
                "steps": [{"file": "", "command": "docker ps"}],
            },
            "niveau non réussi",
        ),
        (
            {**ENVELOPE, "lab": "sql", "level": "x", "dialect": "mysql"},
            "simulation ou niveau inconnu",
        ),
        (
            {**ENVELOPE, "lab": "sql", "level": "plus-cheres", "dialect": "mysql"},
            "requête illisible",
        ),
        (
            {
                **ENVELOPE,
                "lab": "sql",
                "level": "plus-cheres",
                "dialect": "mysql",
                "query": "SELECT 1",
            },
            "niveau non réussi",
        ),
        ({**ENVELOPE, "lab": "circuit", "level": "x"}, "simulation ou niveau inconnu"),
        (
            {
                **ENVELOPE,
                "lab": "circuit",
                "level": "lampe-simple",
                "schema": {
                    "components": [{"id": "pile", "type": "pile", "x": [], "y": 0}]
                },
            },
            "Trop de composants : Source de tension continue.",
        ),
        (
            {
                **ENVELOPE,
                "lab": "circuit",
                "level": "lampe-simple",
                "schema": {
                    "components": [{"id": "lampe_bornes", "type": "lampe_bornes"}]
                },
            },
            "niveau non réussi",
        ),
        ({**ENVELOPE, "lab": "puzzles", "answers": None}, "série incomplète"),
        ({**ENVELOPE, "lab": "oral", "session": {"mode": "x"}}, "séance illisible"),
    ],
)
def test_phone_results_are_refused_with_a_reason(tmp_path, pItem, pReason):
    """Vérifie que chaque partie illisible ou ratée est refusée, avec sa raison."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)

    vReport = sync_lab_results(vDatabaseFile, [pItem])

    assert vReport["saved"] == 0
    assert vReport["rejected"][0]["reason"] == pReason


def test_too_many_phone_results_are_refused(tmp_path):
    """Vérifie le plafond de parties par envoi."""

    with pytest.raises(ValueError):
        sync_lab_results(tmp_path / "scraper.db", [{}] * 201)


def test_phone_oral_session_is_graded_again(tmp_path):
    """Vérifie une séance orale du téléphone renotée par le PC, avec ses points."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    vPackage = build_labs_package(vDatabaseFile)["oral"]

    assert set(vPackage["questions"]) == {"general", "tricky", "technical"}

    vReport = sync_lab_results(
        vDatabaseFile,
        [
            {
                **ENVELOPE,
                "lab": "oral",
                "session": {
                    "mode": "general",
                    "duration": 60,
                    "answers": [{"seconds": 40, "structure": 2, "example": 2}] * 5,
                },
            }
        ],
    )

    assert (vReport["saved"], vReport["xp"]) == (1, 25)
    assert build_labs_package(vDatabaseFile)["oral"]["recent"] == [100]
