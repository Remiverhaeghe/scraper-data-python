"""Tests de la mise en forme des offres commune aux interfaces"""

from datetime import datetime

from job.presentation import FOLLOW_UP_FILTER, build_offer_filters


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
