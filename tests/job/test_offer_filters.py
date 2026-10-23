"""Tests des filtres de la liste des offres"""

from datetime import datetime

from job.offer_filters import OfferFilterChoices, build_offer_filters
from job.presentation import FOLLOW_UP_FILTER

HOME = {"label": "Lille", "latitude": 50.63, "longitude": 3.06}


def test_build_offer_filters_keeps_known_values():
    """Vérifie la traduction des filtres valides."""

    vNow = datetime(2026, 10, 10, 12, 0)

    rFilters = build_offer_filters(
        OfferFilterChoices(
            search="  java ",
            source="adzuna",
            contract="CDI",
            remote=True,
            min_net_salary=2500,
            new_only=True,
            status="APPLIED",
        ),
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
        "pExcludedCompanies": [],
        "pPreferredCompanies": None,
        "pCountry": None,
        "pHiddenAgencies": None,
        "pHiddenCompanies": None,
        "pHideTraining": False,
        "pNear": None,
    }


def test_build_offer_filters_ignores_unknown_values():
    """Vérifie qu'une valeur inconnue ne filtre rien."""

    rFilters = build_offer_filters(
        OfferFilterChoices(
            search="   ",
            source="inconnue",
            contract="STAGE",
            status="NEW",
            availability="jamais",
            distance_km=33,
        ),
        pHome=HOME,
    )

    assert rFilters["pSearch"] is None
    assert rFilters["pSource"] is None
    assert rFilters["pContract"] is None
    assert rFilters["pStatus"] is None
    assert rFilters["pSeenSince"] is None
    assert rFilters["pAvailability"] is None
    assert rFilters["pNear"] is None


def test_build_offer_filters_selects_follow_ups():
    """Vérifie que le filtre « À relancer » porte sur la date du jour."""

    vNow = datetime(2026, 10, 10)

    rFilters = build_offer_filters(
        OfferFilterChoices(status=FOLLOW_UP_FILTER), pNow=vNow
    )

    assert rFilters["pFollowUpBefore"] == vNow
    assert rFilters["pStatus"] is None


def test_build_offer_filters_with_context():
    """Vérifie les filtres qui dépendent du contexte : agences, domicile, France."""

    rFilters = build_offer_filters(
        OfferFilterChoices(
            hide_agencies=True, distance_km=25, france_only=True, preferred_only=True
        ),
        pCompanyKeys={"excluded": ["acme"], "preferred": ["globex"]},
        pAgencies=["proman"],
        pHome=HOME,
        pKeys=[("lever", "1")],
    )

    assert rFilters["pHiddenAgencies"] == ["proman"]
    assert rFilters["pNear"] == {"latitude": 50.63, "longitude": 3.06, "radius_km": 25}
    assert rFilters["pCountry"] == "France"
    assert rFilters["pPreferredCompanies"] == ["globex"]
    assert rFilters["pExcludedCompanies"] == ["acme"]
    assert rFilters["pKeys"] == [("lever", "1")]
    assert build_offer_filters(OfferFilterChoices(distance_km=25))["pNear"] is None
