"""Tests de l'offre créée depuis le lien d'une annonce"""

import json
from datetime import datetime

import pytest
import requests

import job.offer_from_link as offer_from_link
from job.offer_from_link import add_offer_from_link, fetch_offer_fields
from storage.database import initialize_database
from storage.job_offers import get_offer

POSTING = {
    "@context": "https://schema.org",
    "@type": "JobPosting",
    "title": "Développeur Java",
    "description": "<p>Missions : <b>API</b> et SQL.</p>",
    "employmentType": "CONTRACTOR",
    "hiringOrganization": {"@type": "Organization", "name": "Acme"},
    "jobLocation": [{"address": {"addressLocality": "Roubaix", "postalCode": "59100"}}],
    "baseSalary": {
        "currency": "EUR",
        "value": {"minValue": 40000, "maxValue": 50000, "unitText": "YEAR"},
    },
}


def build_page(pData):
    """Construit une page qui embarque une fiche JSON-LD."""

    rPage = (
        '<html><head><script type="application/ld+json">'
        + json.dumps(pData)
        + "</script></head><body>Annonce</body></html>"
    ).encode("utf-8")

    return rPage


def test_job_posting_is_read_even_inside_a_graph(monkeypatch):
    """Vérifie la lecture des champs, fiche seule ou dans un @graph."""

    monkeypatch.setattr(
        offer_from_link,
        "request_bytes",
        lambda *pArgs, **pKwargs: build_page(
            {"@graph": [{"@type": "WebPage"}, POSTING]}
        ),
    )

    vFields = fetch_offer_fields("https://exemple.fr/offre/1")

    assert vFields == {
        "title": "Développeur Java",
        "company": "Acme",
        "url": "https://exemple.fr/offre/1",
        "description": "Missions : API et SQL.",
        "location": "59100 Roubaix",
        "contract": "FREELANCE",
        "salary_label": "40000 - 50000 EUR year",
        "remote": None,
    }


def test_page_without_posting_or_refused_is_explained(monkeypatch):
    """Vérifie les deux refus : page sans fiche, et site qui bloque la lecture."""

    monkeypatch.setattr(
        offer_from_link, "request_bytes", lambda *pArgs, **pKwargs: b"<html></html>"
    )

    with pytest.raises(ValueError, match="Aucune fiche"):
        fetch_offer_fields("https://exemple.fr/offre/2")

    def refuse(*_pArgs, **_pKwargs):
        raise requests.HTTPError("403")

    monkeypatch.setattr(offer_from_link, "request_bytes", refuse)

    with pytest.raises(ValueError, match="Page inaccessible"):
        fetch_offer_fields("https://exemple.fr/offre/3")


def test_offer_is_created_from_the_link(tmp_path, monkeypatch):
    """Vérifie la création de l'offre manuelle à partir du lien."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    monkeypatch.setattr(
        offer_from_link, "request_bytes", lambda *pArgs, **pKwargs: build_page(POSTING)
    )

    vSourceId = add_offer_from_link(
        vDatabaseFile, "https://exemple.fr/offre/1", datetime(2026, 10, 24)
    )

    assert get_offer(vDatabaseFile, "manual", vSourceId)["company"] == "Acme"
