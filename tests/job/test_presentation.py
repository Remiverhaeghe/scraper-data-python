"""Tests de la mise en forme des offres commune aux interfaces"""

from datetime import datetime

import pytest

from job.presentation import (
    FOLLOW_UP_FILTER,
    build_offer_filters,
    describe_search,
    describe_sources,
    prepare_offer,
    summarize_history,
)


def test_build_offer_filters_keeps_known_values():
    """Vérifie la traduction des filtres valides."""

    vNow = datetime(2026, 10, 10, 12, 0)

    rFilters = build_offer_filters(
        pSearch="  java ",
        pSource="adzuna",
        pContract="CDI",
        pRemote=True,
        pMinNetSalary=2500,
        pNewOnly=True,
        pStatus="APPLIED",
        pNow=vNow,
    )

    assert rFilters == {
        "pSearch": "java",
        "pSource": "adzuna",
        "pContract": "CDI",
        "pRemote": True,
        "pMinNetSalary": 2500,
        "pSeenSince": datetime(2026, 10, 7, 12, 0),
        "pStatus": "APPLIED",
        "pFollowUpBefore": None,
        "pHideIgnored": True,
        "pMaxNetSalary": None,
        "pPublishedSince": None,
        "pHasSalary": False,
        "pKeys": None,
        "pAvailability": "available",
        "pNow": vNow,
        "pExpiredBefore": datetime(2026, 9, 10, 12, 0),
    }


def test_build_offer_filters_ignores_unknown_values():
    """Vérifie qu'une valeur inconnue ne filtre rien."""

    rFilters = build_offer_filters(
        pSearch="   ", pSource="inconnue", pContract="STAGE", pStatus="NEW"
    )

    assert rFilters["pSearch"] is None
    assert rFilters["pSource"] is None
    assert rFilters["pContract"] is None
    assert rFilters["pStatus"] is None
    assert rFilters["pSeenSince"] is None


def test_build_offer_filters_selects_follow_ups():
    """Vérifie que le filtre « À relancer » porte sur la date du jour."""

    vNow = datetime(2026, 10, 10)

    rFilters = build_offer_filters(pStatus=FOLLOW_UP_FILTER, pNow=vNow)

    assert rFilters["pFollowUpBefore"] == vNow
    assert rFilters["pStatus"] is None


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
