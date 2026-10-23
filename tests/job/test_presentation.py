"""Tests de la mise en forme des offres commune aux interfaces"""

from datetime import datetime

import pytest

from job.presentation import (
    build_translate_url,
    can_lookup_company,
    describe_search,
    describe_sources,
    get_score_tone,
    is_french,
    prepare_offer,
    summarize_history,
    to_list,
)


def test_describe_search():
    """Vérifie le résumé des critères d'une recherche enregistrée."""

    vParameters = {
        "keyword": "Java",
        "location": "Lille",
        "contract": "CDI",
        "min_salary": 2500,
        "remote": True,
    }

    assert describe_search(vParameters) == (
        "Java · Lille · CDI · ≥ 2\u202f500 € net · télétravail"
    )
    assert describe_search({"sources": ["adzuna"]}) == "Sans critère"
    assert describe_search({}) == "Sans critère"
    assert describe_search(None) == ""


def test_describe_sources():
    """Vérifie l'affichage des libellés des sources, même inconnues."""

    assert describe_sources({"sources": ["adzuna", "ancienne"]}) == "Adzuna, ancienne"
    assert describe_sources(None) == ""


def test_summarize_history():
    """Vérifie la mise en forme de la synthèse de l'historique."""

    assert summarize_history(
        {"executions": 4, "item_count": 120, "average_duration": 2.345, "successes": 3}
    ) == {
        "executions": 4,
        "item_count": 120,
        "average_duration": "2.3 s",
        "success_rate": "75 %",
    }
    assert (
        summarize_history(
            {"executions": 0, "item_count": 0, "average_duration": 0, "successes": 0}
        )["success_rate"]
        == "-"
    )


@pytest.mark.parametrize(
    "pStored, pExpected", [("1", True), ("0", False), (None, None), (True, True)]
)
def test_prepare_offer_converts_stored_remote(pStored, pExpected):
    """Vérifie que la valeur texte '0' n'est pas prise pour du télétravail."""

    vOffer = prepare_offer(
        {
            "source": "adzuna",
            "source_id": "1",
            "first_seen_at": "2026-10-10",
            "last_seen_at": "2026-10-10",
            "remote": pStored,
        },
        datetime(2026, 10, 1),
        datetime(2026, 10, 11),
    )

    assert vOffer["remote"] is pExpected


@pytest.mark.parametrize(
    "pText, pFrench",
    [
        ("Nous recherchons un développeur pour rejoindre notre équipe à Lille", True),
        ("Wir suchen neue Mitarbeiter für unser Team in Düsseldorf", False),
        ("We are looking for a senior engineer to join the team", False),
        ("", False),
    ],
)
def test_is_french(pText, pFrench):
    """Vérifie la détection d'un texte français par ses mots outils."""

    assert is_french(pText) is pFrench


def test_build_translate_url_only_for_foreign_text():
    """Vérifie le lien de traduction, absent pour un texte français ou vide."""

    vUrl = build_translate_url(
        "Wir suchen neue Mitarbeiter für unser Team " + "x" * 5000
    )

    assert vUrl.startswith("https://translate.google.com/?sl=auto&tl=fr")
    assert "Wir%20suchen" in vUrl
    assert len(vUrl) < 4200
    assert (
        build_translate_url("Nous recherchons un développeur pour notre équipe") is None
    )
    assert build_translate_url("Wir suchen") is None
    assert build_translate_url(None) is None


@pytest.mark.parametrize(
    "pOffer, pPossible",
    [
        ({"company": "Acme", "country": "France"}, True),
        ({"company": "Acme", "country": None}, True),
        ({"company": "Acme", "country": "Allemagne"}, False),
        ({"company": "Acme", "country": None, "location": "Nürnberg"}, False),
        ({"company": None, "country": "France"}, False),
    ],
)
def test_can_lookup_company(pOffer, pPossible):
    """Vérifie que l'annuaire n'est proposé que pour une entreprise française."""

    assert can_lookup_company(pOffer) is pPossible


@pytest.mark.parametrize(
    "pScore, pLowTone, pExpected",
    [
        (70, "muted", "success"),
        (40, "muted", "warning"),
        (39, "muted", "muted"),
        (10, "danger", "danger"),
    ],
)
def test_get_score_tone(pScore, pLowTone, pExpected):
    """Vérifie les seuils communs de couleur des scores."""

    assert get_score_tone(pScore, pLowTone) == pExpected


def test_to_list_reads_json_and_ignores_missing_values():
    """Vérifie la lecture d'une liste JSON, d'un texte, et d'une valeur manquante."""

    assert to_list('["Java", "SQL"]') == ["Java", "SQL"]
    assert to_list("Java") == ["Java"]
    assert to_list(["Go"]) == ["Go"]
    assert to_list(float("nan")) == []
    assert to_list(None) == []
