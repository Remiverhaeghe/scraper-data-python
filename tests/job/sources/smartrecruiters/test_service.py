"""Tests de la source SmartRecruiters"""

import requests

from job.sources.smartrecruiters import service
from job.sources.smartrecruiters.parser import parse_posting, read_description
from job.sources.smartrecruiters.service import scrape_jobs

POSTING = {
    "id": "744000154883219",
    "name": "Technicien de Maintenance H/F - Lille",
    "company": {"identifier": "Loxam", "name": "Loxam Rental"},
    "releasedDate": "2026-10-11T15:27:45.341Z",
    "location": {
        "city": "Fretin",
        "country": "fr",
        "postalCode": "59273",
        "fullLocation": "Fretin, Hauts-de-France, France",
        "remote": False,
        "hybrid": False,
    },
    "industry": {"id": "facilities", "label": "Facilities Services"},
    "function": {"id": "other", "label": "Other"},
    "typeOfEmployment": {"id": "permanent", "label": "Full-time"},
    "experienceLevel": {"id": "mid", "label": "Mid-Senior Level"},
}

DETAIL = {
    "postingUrl": "https://jobs.smartrecruiters.com/Loxam/744000154883219-technicien",
    "jobAd": {
        "sections": {
            "jobDescription": {"text": "<p>Maintenance des nacelles</p>"},
            "qualifications": {"text": "<p>Électromécanique</p>"},
            "additionalInformation": {"text": ""},
        }
    },
}


def test_parse_posting_and_description():
    """Vérifie la lecture d'une offre de la liste et de son détail."""

    vJob = parse_posting(POSTING, "Loxam")

    assert vJob["title"] == "Technicien de Maintenance H/F - Lille"
    assert vJob["company"] == "Loxam Rental"
    assert vJob["source_id"] == "744000154883219"
    assert vJob["country"] == "FR"
    assert vJob["postal_code"] == "59273"
    assert vJob["contract_type"] == "Full-time"
    assert vJob["description"] is None
    assert read_description(DETAIL) == "Maintenance des nacelles\n\nÉlectromécanique"
    assert read_description({}) is None


def test_scrape_reads_details_only_for_matching_postings(monkeypatch):
    """Vérifie le filtre sur la liste avant tout appel de détail."""

    vOther = {**POSTING, "id": "2", "name": "Commercial sédentaire"}
    vDetails = []
    monkeypatch.setattr(
        service,
        "get_postings",
        lambda *_pArgs: {"content": [POSTING, vOther], "totalFound": 2},
    )
    monkeypatch.setattr(
        service,
        "get_posting",
        lambda _pCompany, pId: vDetails.append(pId) or DETAIL,
    )

    vJobs = scrape_jobs("Loxam", "fr", "maintenance", "Fretin", 10)

    assert vDetails == ["744000154883219"]
    assert vJobs.iloc[0]["description"].startswith("Maintenance des nacelles")
    assert vJobs.iloc[0]["url"] == DETAIL["postingUrl"]


def test_unavailable_detail_keeps_the_posting(monkeypatch):
    """Vérifie qu'une offre retirée entre la liste et le détail reste lisible."""

    monkeypatch.setattr(
        service, "get_postings", lambda *_pArgs: {"content": [POSTING], "totalFound": 1}
    )

    def fail(*_pArgs):
        raise requests.HTTPError("404")

    monkeypatch.setattr(service, "get_posting", fail)

    vJobs = scrape_jobs("Loxam", "fr")

    assert len(vJobs) == 1
    assert vJobs.iloc[0]["url"].endswith("/Loxam/744000154883219")
