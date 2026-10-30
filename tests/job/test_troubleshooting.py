"""Tests des pannes à résoudre : scénarios, partie rejouée, score et points"""

from datetime import datetime

import pytest

from job.progress import load_activity
from job.troubleshooting import (
    build_overview,
    get_stars,
    load_scenarios,
    parse_actions,
    play,
    save_result,
)
from storage.database import initialize_database

NOW = datetime(2026, 10, 30, 10, 0)


@pytest.mark.parametrize("pScenario", list(load_scenarios().values()))
def test_scenarios_are_consistent(pScenario):
    """Vérifie une seule bonne réparation, une preuve, des identifiants uniques."""

    vCheckIds = [vCheck["id"] for vCheck in pScenario["checks"]]
    vCauseIds = [vCause["id"] for vCause in pScenario["causes"]]

    assert sum(bool(vCause.get("right")) for vCause in pScenario["causes"]) == 1
    assert any(vCheck.get("evidence") for vCheck in pScenario["checks"])
    assert len(set(vCheckIds)) == len(vCheckIds)
    assert len(set(vCauseIds)) == len(vCauseIds)
    assert all(
        vCheck["requires"] in vCheckIds
        for vCheck in pScenario["checks"]
        if vCheck.get("requires")
    )
    assert pScenario["best_minutes"] > 0


def test_play_refuses_unsafe_checks_and_counts_wrong_repairs():
    """Vérifie la consignation exigée, la pièce remplacée pour rien et le score."""

    vState = play(
        "convoyeur-arret",
        parse_actions(
            "check:resistance-bobine,repair:moteur,check:consigner,"
            "check:resistance-bobine,repair:bobine-km1,check:fusibles"
        ),
    )

    assert vState["log"][0]["refused"] and vState["log"][0]["minutes"] == 0
    assert vState["wrong"] == ["moteur"]
    assert vState["solved"] and vState["proven"]
    assert vState["minutes"] == 90 + 5 + 3 + 15
    assert vState["score"] == round(100 * 20 / 113) - 15
    assert "fusibles" not in vState["done"]


def test_unproven_repair_is_capped_and_unsolved_has_no_score():
    """Vérifie le plafond d'une réparation devinée et l'absence de score en cours."""

    assert play("verin-lent", ["repair:silencieux"])["score"] == 50
    assert play("verin-lent", ["check:reseau"])["score"] is None
    assert [get_stars(vScore) for vScore in (100, 80, 79, 50, 10)] == [3, 3, 2, 2, 1]

    with pytest.raises(ValueError):
        play("inconnu", [])


def test_result_is_saved_rewarded_and_summarized(tmp_path):
    """Vérifie l'enregistrement, les points gagnés et la vue d'ensemble."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)

    vXp = save_result(
        vDatabaseFile,
        play("verin-lent", ["check:silencieux", "repair:silencieux"]),
        NOW,
    )
    vRow = next(
        vRow
        for vRow in build_overview(vDatabaseFile)["rows"]
        if vRow["id"] == "verin-lent"
    )

    assert vXp == 20 + 2 * 10
    assert load_activity(vDatabaseFile)[NOW.date()]["xp"] == vXp
    assert (vRow["attempts"], vRow["best"], vRow["stars"]) == (1, 100, 3)
