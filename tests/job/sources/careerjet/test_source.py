"""Tests de la source Careerjet"""

from types import SimpleNamespace

import pytest

from job.sources.careerjet import client, source
from job.sources.careerjet.config import load_config
from job.sources.careerjet.parser import parse_job

JOB = {
    "title": "Automaticien H/F",
    "company": "Industrie SA",
    "date": "Wed, 21 Oct 2026 09:00:00 GMT",
    "description": "Programmation <b>Siemens</b>",
    "locations": "Lille",
    "salary": "35 000 - 40 000 €",
    "salary_currency_code": "EUR",
    "salary_min": 35000,
    "salary_max": 40000,
    "salary_type": "Y",
    "url": "https://jobviewtrack.com/v2/abc",
}


def test_parse_job_builds_a_stable_identifier():
    """Vérifie la lecture d'une offre et un identifiant indépendant du lien."""

    vJob = parse_job(JOB)

    assert vJob["salary_period"] == "year"
    assert vJob["published_at"].startswith("2026-10-21T09:00:00")
    assert vJob["description"] == "Programmation Siemens"
    assert vJob["source_id"] == parse_job({**JOB, "url": "https://autre"})["source_id"]


def test_missing_key_is_reported(monkeypatch):
    """Vérifie que la source reste non configurée sans clé d'éditeur."""

    monkeypatch.delenv("CAREERJET_API_KEY", raising=False)

    assert source.SOURCE.get_unavailability_reason() == "non configurée"

    with pytest.raises(ValueError, match="CAREERJET_API_KEY"):
        load_config()


def test_scrape_pages_until_the_limit(monkeypatch):
    """Vérifie la lecture page par page, l'authentification et la limite."""

    monkeypatch.setenv("CAREERJET_API_KEY", "cle")
    vCalls = []

    def fake_request(_pMethod, _pUrl, **pOptions):
        vCalls.append(pOptions)
        vPage = pOptions["pParams"]["page"]
        return {
            "pages": 5,
            "jobs": [
                {**JOB, "title": f"Poste {vPage}-{vIndex}"}
                for vIndex in range(client.PAGE_SIZE)
            ],
        }

    monkeypatch.setattr(client, "request_json", fake_request)
    vConfig = SimpleNamespace(
        keyword="automaticien", location="Lille", max_items=150, max_pages=None
    )

    vJobs = source.SOURCE.scrape(source.load_parameters(vConfig), vConfig)

    assert len(vJobs) == 150
    assert len(vCalls) == 2
    assert vCalls[0]["pAuth"] == ("cle", "")
    assert vCalls[0]["pParams"]["user_ip"] and vCalls[0]["pParams"]["user_agent"]
