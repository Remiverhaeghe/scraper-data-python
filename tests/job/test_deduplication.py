"""Tests du repérage des offres publiées plusieurs fois"""

from datetime import datetime

import pandas as pd
import pytest

from job.deduplication import (
    MERGED,
    SEPARATE,
    find_differences,
    get_offer_group,
    group_offers,
)
from job.fingerprint import build_fingerprint, normalize_city
from storage.database import initialize_database
from storage.duplicates import get_decisions, save_decision
from storage.job_offers import save_offers


@pytest.mark.parametrize(
    "pOffer, pExpected",
    [
        (
            {
                "title": "Développeur Java H/F",
                "company": "Acme SAS",
                "location": "Lille (59)",
            },
            "developpeur java|acme|lille",
        ),
        (
            {
                "title": "Developpeur java (F/H)",
                "company": "ACME",
                "location": "59000 Lille, France",
            },
            "developpeur java|acme|lille",
        ),
        (
            {
                "title": "Data Engineer (m/w/d)",
                "company": "Foo GmbH",
                "location": "Berlin - Mitte",
            },
            "data engineer|foo|berlin",
        ),
        ({"title": "", "company": "Acme"}, None),
    ],
)
def test_build_fingerprint(pOffer, pExpected):
    """Vérifie que deux écritures d'une même offre donnent la même empreinte."""

    assert build_fingerprint(pOffer) == pExpected


def test_normalize_city_without_location():
    """Vérifie qu'un lieu absent donne une ville vide."""

    assert normalize_city(None) == ""


def build_offer(pSourceId, pSourceLabel, **pValues):
    """Construit une offre préparée appartenant au groupe « dev|acme|lille »."""

    rOffer = {
        "source_id": pSourceId,
        "source_label": pSourceLabel,
        "fingerprint": "dev|acme|lille",
        "contract": "CDI",
        "net_salary": "2 500 €",
        "location": "Lille",
        "remote": True,
    }

    rOffer.update(pValues)

    return rOffer


def test_find_differences_ignores_missing_values():
    """Vérifie qu'une valeur absente n'est pas comptée comme une différence."""

    assert (
        find_differences(
            [build_offer("1", "Adzuna"), build_offer("2", "Jooble", net_salary=None)]
        )
        == []
    )
    assert find_differences(
        [build_offer("1", "Adzuna"), build_offer("2", "Jooble", contract="CDD")]
    ) == ["Contrat"]


@pytest.mark.parametrize(
    "pDecision, pRows, pNeedsReview",
    [(None, 1, True), (MERGED, 1, False), (SEPARATE, 2, False)],
)
def test_group_offers_follows_decisions(pDecision, pRows, pNeedsReview):
    """Vérifie le regroupement, la validation demandée et l'effet des décisions."""

    vDecisions = {"dev|acme|lille": pDecision} if pDecision else {}

    rOffers = group_offers(
        [build_offer("1", "Adzuna"), build_offer("2", "Jooble", contract="CDD")],
        vDecisions,
    )

    assert len(rOffers) == pRows
    assert rOffers[0]["needs_review"] is pNeedsReview

    if pRows == 1:
        assert rOffers[0]["source_labels"] == ["Adzuna", "Jooble"]
        assert [vOffer["source_id"] for vOffer in rOffers[0]["duplicates"]] == ["2"]


def test_offers_without_fingerprint_stay_alone():
    """Vérifie qu'une offre sans empreinte n'est jamais regroupée."""

    rOffers = group_offers(
        [
            build_offer("1", "Adzuna", fingerprint=None),
            build_offer("2", "Adzuna", fingerprint=None),
        ],
        {},
    )

    assert len(rOffers) == 2


def test_get_offer_group_and_decisions(tmp_path):
    """Vérifie la lecture des annonces d'une offre et l'enregistrement d'une décision."""

    vDatabaseFile = tmp_path / "scraper.db"

    initialize_database(vDatabaseFile)
    save_offers(
        vDatabaseFile,
        pd.DataFrame(
            [
                {
                    "source": "adzuna",
                    "source_id": "1",
                    "title": "Dev",
                    "contract": "CDI",
                    "fingerprint": "dev|acme|lille",
                },
                {
                    "source": "jooble",
                    "source_id": "2",
                    "title": "Dev",
                    "contract": "CDD",
                    "fingerprint": "dev|acme|lille",
                },
            ]
        ),
        datetime(2026, 10, 11),
    )
    save_decision(vDatabaseFile, "dev|acme|lille", MERGED, datetime(2026, 10, 11))

    rGroup = get_offer_group(
        vDatabaseFile, {"fingerprint": "dev|acme|lille"}, lambda pOffer: pOffer
    )

    assert sorted(vOffer["source"] for vOffer in rGroup["offers"]) == [
        "adzuna",
        "jooble",
    ]
    assert rGroup["differences"] == ["Contrat"]
    assert rGroup["decision"] == MERGED
    assert get_decisions(vDatabaseFile) == {"dev|acme|lille": MERGED}
