"""Tests de la description lue à l'ouverture d'une offre"""

import pandas as pd
import requests

import job.offer_details as offer_details
from job.offer_details import (
    can_fetch_description,
    complete_missing_descriptions,
    fetch_missing_description,
)
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


def build_response_error(pStatusCode):
    """Retourne l'erreur HTTP levée par une réponse de ce code."""

    vResponse = requests.Response()
    vResponse.status_code = pStatusCode

    rError = requests.HTTPError(str(pStatusCode), response=vResponse)

    return rError


def test_search_keeps_a_description_read_later(tmp_path):
    """Vérifie qu'une recherche sans description n'efface pas celle déjà lue."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    save_offers(
        vDatabaseFile,
        pd.DataFrame([{**OFFER, "description": "Maintenance"}]),
        pd.Timestamp("2026-10-23"),
    )
    save_offers(
        vDatabaseFile,
        pd.DataFrame([{**OFFER, "description": None}]),
        pd.Timestamp("2026-10-24"),
    )

    assert get_offer(vDatabaseFile, "smartrecruiters", "744")["description"] == (
        "Maintenance"
    )


def test_missing_descriptions_are_completed_by_batch(tmp_path, monkeypatch):
    """Vérifie le lot de fond : lue, retirée notée, panne qui arrête le passage."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    save_offers(
        vDatabaseFile,
        pd.DataFrame(
            [
                {**OFFER, "source_id": vId}
                for vId in ("lue", "retiree", "redirigee", "panne", "suivante")
            ]
        ),
        pd.Timestamp("2026-10-23"),
    )
    vOutcomes = {
        "lue": ("Maintenance", OFFER["url"]),
        "retiree": build_response_error(404),
        "redirigee": ValueError("Redirection refusée"),
        "panne": requests.ConnectionError("hors ligne"),
    }
    vCalls = []

    def fetch(pOffer):
        vCalls.append(pOffer["source_id"])
        vOutcome = vOutcomes[pOffer["source_id"]]

        if isinstance(vOutcome, Exception):
            raise vOutcome

        return vOutcome

    monkeypatch.setitem(offer_details.DESCRIPTION_FETCHERS, "smartrecruiters", fetch)
    monkeypatch.setattr(
        offer_details,
        "get_offers_without_description",
        lambda pDatabaseFile, pSources, pLimit: [
            {**OFFER, "source_id": vId, "description": None}
            for vId in ("lue", "retiree", "redirigee", "panne", "suivante")
        ][:pLimit],
    )

    vReport = complete_missing_descriptions(vDatabaseFile)

    assert vReport == {"read": 1, "unavailable": 2}
    assert vCalls == ["lue", "retiree", "redirigee", "panne"]
    assert get_offer(vDatabaseFile, "smartrecruiters", "lue")["description"] == (
        "Maintenance"
    )
    assert get_offer(vDatabaseFile, "smartrecruiters", "retiree")["description"] == ""
    assert get_offer(vDatabaseFile, "smartrecruiters", "panne")["description"] is None


def test_server_errors_stop_the_pass_without_marking(tmp_path, monkeypatch):
    """Vérifie qu'une erreur 503 ou 429 n'est pas prise pour une offre retirée."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    save_offers(vDatabaseFile, pd.DataFrame([OFFER]), pd.Timestamp("2026-10-23"))

    for vStatusCode in (503, 429):

        def fail(_pOffer, pStatusCode=vStatusCode):
            raise build_response_error(pStatusCode)

        monkeypatch.setitem(offer_details.DESCRIPTION_FETCHERS, "smartrecruiters", fail)

        assert complete_missing_descriptions(vDatabaseFile) == {
            "read": 0,
            "unavailable": 0,
        }

    assert get_offer(vDatabaseFile, "smartrecruiters", "744")["description"] is None
