"""Tests du jeu de négociation salariale : budget, réactions du recruteur, score"""

from datetime import datetime

import pytest

import job.salary_negotiation as negotiation
from job.progress import load_activity
from job.salary_negotiation import (
    build_budget,
    build_negotiation_view,
    play_negotiation,
    start_negotiation,
)
from storage.database import initialize_database

NOW = datetime(2026, 10, 31, 9, 0)
BUDGET = {
    "median": 36000,
    "low": 32000,
    "high": 40000,
    "target": 38000,
    "ceiling": 42000,
}


@pytest.fixture
def database_file(tmp_path, monkeypatch):
    """Fournit une base vide et un marché fixe."""

    rDatabaseFile = tmp_path / "scraper.db"
    initialize_database(rDatabaseFile)
    monkeypatch.setattr(negotiation, "build_budget", lambda *pArgs: dict(BUDGET))

    return rDatabaseFile


def play(pDatabaseFile, *pChoices):
    """Commence une partie et joue les réponses ; retourne la partie finale."""

    start_negotiation(pDatabaseFile, {"title": "Technicien", "company": "Acme"})

    for vChoice in pChoices:
        rGame = play_negotiation(pDatabaseFile, vChoice, NOW)

    return rGame


def test_budget_comes_from_the_offer_market_then_the_global_median(
    tmp_path, monkeypatch
):
    """Vérifie les montants en brut annuel, d'après l'offre ou la médiane globale."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    monkeypatch.setattr(
        negotiation,
        "find_market_salary",
        lambda *pArgs: {"median": 2500, "low": 2200, "high": 2800, "target": 2600},
    )
    vBudget = build_budget(vDatabaseFile, {"title": "x"})

    assert vBudget["low"] < vBudget["median"] < vBudget["high"] < vBudget["ceiling"]
    assert vBudget["median"] < vBudget["target"] < vBudget["high"]
    assert vBudget["median"] % 100 == 0

    monkeypatch.setattr(negotiation, "find_market_salary", lambda *pArgs: None)
    monkeypatch.setattr(negotiation, "load_market_median", lambda *pArgs: 2500)

    assert build_budget(vDatabaseFile, None)["target"] == vBudget["median"]

    monkeypatch.setattr(negotiation, "load_market_median", lambda *pArgs: None)

    with pytest.raises(ValueError):
        build_budget(vDatabaseFile, None)


def test_anchored_argued_negotiation_scores_well(database_file):
    """Vérifie le meilleur parcours : fourchette, argument, avantages."""

    vGame = play(database_file, "range", "argue", "benefits")

    assert vGame["deal"] and vGame["offer"] == 37800
    assert vGame["score"] == 98
    assert any("bonne pratique" in vAdvice for vAdvice in vGame["advice"])
    assert vGame["transcript"][-1][1].startswith("Entendu pour")
    assert build_negotiation_view(database_file)["best"] == 98
    assert load_activity(database_file)[NOW.date()]["actions"]["negotiation"] == 1


def test_letting_the_recruiter_anchor_costs_money(database_file):
    """Vérifie l'offre basse sans ancrage, acceptée telle quelle, et ses conseils."""

    vGame = play(database_file, "let", "accept")

    assert vGame["offer"] == 32000 and vGame["score"] == 20
    assert any(
        vAdvice.startswith("Laisser le recruteur") for vAdvice in vGame["advice"]
    )
    assert any("il restait de la marge" in vAdvice for vAdvice in vGame["advice"])


@pytest.mark.parametrize(
    "pChoices, pDeal, pTrust",
    [
        (("high", "ultimatum", "accept"), True, 1),
        (("low", "counter", "refuse"), False, 3),
        (("range", "benefits", "accept"), True, 3),
    ],
)
def test_recruiter_reacts_to_each_answer(database_file, pChoices, pDeal, pTrust):
    """Vérifie la confiance entamée et la fin de partie selon les réponses."""

    vGame = play(database_file, *pChoices)

    assert (vGame["deal"], vGame["trust"]) == (pDeal, pTrust)
    assert vGame["choices"] == []


def test_ultimatum_above_the_budget_ends_without_a_deal(database_file, monkeypatch):
    """Vérifie l'ultimatum au-dessus du plafond : pas d'accord, refus défendable."""

    monkeypatch.setattr(
        negotiation, "build_budget", lambda *pArgs: {**BUDGET, "target": 45000}
    )
    vGame = play(database_file, "let", "ultimatum")

    assert (vGame["deal"], vGame["score"], vGame["trust"]) == (False, 40, 1)


def test_unknown_answers_are_refused(database_file):
    """Vérifie le refus d'une réponse hors partie ou hors des choix proposés."""

    with pytest.raises(ValueError, match="Aucune"):
        play_negotiation(database_file, "range")

    start_negotiation(database_file)

    with pytest.raises(ValueError, match="Réponse inconnue"):
        play_negotiation(database_file, "accept")

    assert [
        vId for vId, _ in build_negotiation_view(database_file)["game"]["choices"]
    ] == [
        "let",
        "range",
        "high",
        "low",
    ]
