"""Tests de la description lue à l'ouverture d'une offre"""

import pandas as pd
import requests

import job.offer_details as offer_details
from job.offer_details import can_fetch_description, fetch_missing_description
from job.sources.smartrecruiters.service import fetch_description
from storage.database import initialize_database
from storage.job_offers import get_offer, save_offers

OFFER = {
    "source": "smartrecruiters",
    "source_id": "744",
    "title": "Technicien",
    "url": "https://jobs.smartrecruiters.com/Loxam/744",
}


def test_missing_description_is_fetched_and_saved(tmp_path, monkeypatch):
    """Vérifie la lecture, l'enregistrement et l'adresse publique gardée."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    save_offers(vDatabaseFile, pd.DataFrame([OFFER]), pd.Timestamp("2026-10-23"))
    vCalls = []
    monkeypatch.setitem(
        offer_details.DESCRIPTION_FETCHERS,
        "smartrecruiters",
        lambda pOffer: vCalls.append(pOffer["source_id"])
        or ("Maintenance des nacelles", OFFER["url"] + "-technicien"),
    )

    vOffer = fetch_missing_description(
        vDatabaseFile, get_offer(vDatabaseFile, "smartrecruiters", "744")
    )

    assert vCalls == ["744"]
    assert vOffer["description"] == "Maintenance des nacelles"
    assert get_offer(vDatabaseFile, "smartrecruiters", "744")["url"].endswith(
        "-technicien"
    )
    assert not can_fetch_description(vOffer)
    assert not can_fetch_description({**OFFER, "source": "lever"})


def test_unavailable_description_keeps_the_offer(tmp_path, monkeypatch):
    """Vérifie qu'une offre retirée s'affiche quand même, sans description."""

    def fail(_pOffer):
        raise requests.HTTPError("404")

    monkeypatch.setitem(offer_details.DESCRIPTION_FETCHERS, "smartrecruiters", fail)

    assert fetch_missing_description(tmp_path / "scraper.db", OFFER) == OFFER


def test_smartrecruiters_company_is_read_in_the_url(monkeypatch):
    """Vérifie l'identifiant de l'entreprise lu dans l'adresse de l'offre."""

    vCalls = []
    monkeypatch.setattr(
        "job.sources.smartrecruiters.service.get_posting",
        lambda pCompany, pId: vCalls.append((pCompany, pId)) or {},
    )

    assert fetch_description(OFFER) == (None, OFFER["url"])
    assert vCalls == [("Loxam", "744")]
    assert fetch_description({**OFFER, "url": "https://exemple.fr/1"}) is None
