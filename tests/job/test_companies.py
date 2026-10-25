"""Tests des listes d'entreprises et des candidatures déjà envoyées"""

from datetime import datetime, timedelta

import pandas as pd
import pytest

from job.companies import (
    add_company_rule,
    find_preferred_offers,
    build_company_filter_keys,
    describe_company_applications,
    find_company_applications,
    get_company_rule,
    load_company_rules,
    parse_companies,
    save_company_rules,
)
from job.application_tracking import get_week_follow_ups
from job.fingerprint import build_fingerprint
from job.offer_filters import OfferFilterChoices, build_offer_filters
from storage.database import initialize_database
from storage.job_applications import save_application, save_contact_email
from storage.job_offers import get_offers, save_offers

NOW = datetime(2026, 10, 11, 10, 0)


@pytest.fixture
def database_file(tmp_path):
    """Crée une base avec trois offres de deux entreprises."""

    rDatabaseFile = tmp_path / "scraper.db"

    initialize_database(rDatabaseFile)

    vOffers = pd.DataFrame(
        [
            {
                "source": "remotive",
                "source_id": "1",
                "title": "Java",
                "company": "Acme SAS",
            },
            {
                "source": "remotive",
                "source_id": "2",
                "title": "Python",
                "company": "acme",
            },
            {"source": "adzuna", "source_id": "3", "title": "Go", "company": "Globex"},
        ]
    )
    vOffers["fingerprint"] = [
        build_fingerprint(vOffer) for vOffer in vOffers.to_dict("records")
    ]

    save_offers(rDatabaseFile, vOffers, NOW)

    return rDatabaseFile


def test_parse_companies_removes_duplicates():
    """Vérifie le découpage par ligne ou virgule, sans doublon à la forme juridique près."""

    assert parse_companies("Acme SAS, acme\n  Globex  \n\n") == ["Acme SAS", "Globex"]

    with pytest.raises(ValueError, match="trop long"):
        parse_companies("x" * 201)


def test_rules_round_trip_and_conflict(database_file):
    """Vérifie l'enregistrement des listes et le refus d'une entreprise dans les deux."""

    assert load_company_rules(database_file) == {"excluded": [], "preferred": []}

    save_company_rules(database_file, "Globex", "Acme")

    assert load_company_rules(database_file) == {
        "excluded": ["Globex"],
        "preferred": ["Acme"],
    }

    with pytest.raises(ValueError, match="à la fois exclue et privilégiée : acme"):
        save_company_rules(database_file, "ACME", "Acme SARL")

    vRules = add_company_rule(database_file, "Globex Inc", "preferred")

    assert vRules == {"excluded": [], "preferred": ["Acme", "Globex Inc"]}
    assert get_company_rule("GLOBEX", vRules) == "preferred"
    assert get_company_rule("Initech", vRules) is None


def test_filters_hide_excluded_and_keep_preferred(database_file):
    """Vérifie le masquage des entreprises exclues et le filtre des privilégiées."""

    vKeys = build_company_filter_keys({"excluded": ["Acme"], "preferred": ["Globex"]})

    def titles(pPreferredOnly):
        """Retourne les titres affichés avec ces listes."""
        rTitles = sorted(
            get_offers(
                database_file,
                **build_offer_filters(
                    OfferFilterChoices(preferred_only=pPreferredOnly),
                    pNow=NOW,
                    pCompanyKeys=vKeys,
                ),
            )["title"]
        )

        return rTitles

    assert titles(False) == ["Go"]
    assert titles(True) == ["Go"]
    assert get_offers(
        database_file,
        **build_offer_filters(
            OfferFilterChoices(preferred_only=True),
            pNow=NOW,
            pCompanyKeys={"excluded": [], "preferred": []},
        ),
    ).empty


def test_company_applications_warning(database_file):
    """Vérifie l'avertissement d'une candidature déjà envoyée à la même entreprise."""

    vOffer = {"source": "remotive", "source_id": "2", "company": "Acme"}

    assert (
        describe_company_applications(find_company_applications(database_file, vOffer))
        is None
    )

    save_application(database_file, "remotive", "1", "APPLIED", pNow=NOW)
    save_application(database_file, "remotive", "2", "INTERESTED", pNow=NOW)

    assert describe_company_applications(
        find_company_applications(database_file, vOffer)
    ) == ("Déjà 1 candidature(s) dans cette entreprise : Java (Postulé, le 11/10/2026)")


def test_known_contact_is_shared_with_the_company_offers(database_file):
    """Vérifie l'adresse du recruteur rappelée sur les autres offres de l'entreprise."""

    vOffer = {"source": "remotive", "source_id": "2", "company": "Acme"}
    save_application(database_file, "remotive", "1", "APPLIED", pNow=NOW)
    save_contact_email(database_file, "remotive", "1", "rh@acme.fr")

    assert describe_company_applications(
        find_company_applications(database_file, vOffer)
    ).endswith(". Contact connu : rh@acme.fr")

    save_application(database_file, "remotive", "2", "APPLIED", pNow=NOW)

    vCard = next(
        vCard
        for vCard in get_week_follow_ups(database_file, NOW + timedelta(days=8))
        if vCard["source_id"] == "2"
    )

    assert vCard["contact_email"] == "rh@acme.fr"


def test_preferred_companies_offers_are_watched(database_file):
    """Vérifie les offres récentes des entreprises privilégiées, et rien sans liste."""

    vSince = datetime(2000, 1, 1)

    assert find_preferred_offers(database_file, vSince) == []

    save_company_rules(database_file, "", "Acme")

    assert sorted(
        vOffer["source_id"] for vOffer in find_preferred_offers(database_file, vSince)
    ) == ["1", "2"]
