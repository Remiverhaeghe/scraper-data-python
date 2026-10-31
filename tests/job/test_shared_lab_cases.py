"""Cas des simulations communs au PC et au téléphone, et leur intégration"""

import json
from datetime import datetime

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
