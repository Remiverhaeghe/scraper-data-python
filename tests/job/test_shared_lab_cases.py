"""Cas des simulations communs au PC et au téléphone, et leur intégration"""

import json
from datetime import datetime

from job.mobile_labs import build_labs_package, sync_lab_results
from job.troubleshooting import load_results
from storage.database import initialize_database
from tools.lab_cases import FIXTURE_FILE, build_cases


def test_shared_cases_are_up_to_date():
    """Vérifie le fichier commun : à régénérer par python -m tools.lab_cases."""

    vCases = build_cases()

    assert json.loads(FIXTURE_FILE.read_text(encoding="utf-8")) == vCases
    assert {vCase["expected"]["score"] for vCase in vCases["troubleshooting"]} >= {
        12,
        38,
    }


def test_phone_results_are_replayed_and_counted_once(tmp_path):
    """Vérifie la partie rejouée par le PC, l'envoi répété ignoré et les refus."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    vScenario = build_labs_package()["troubleshooting"]["scenarios"][0]
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
