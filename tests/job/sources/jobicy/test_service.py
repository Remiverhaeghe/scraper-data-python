"""Tests du service Jobicy"""

from job.sources.jobicy import service
from job.sources.jobicy.service import scrape_jobs


def test_scrape_jobs_requests_france_with_max_items(monkeypatch):
    """Vérifie la zone géographique et le nombre d'offres demandés."""

    vCalls = []

    def mock_get_jobs(pTag, pGeo, pCount):
        vCalls.append({"tag": pTag, "geo": pGeo, "count": pCount})

        rJobs = [{"id": vId} for vId in range(pCount)]

        return rJobs

    monkeypatch.setattr(service, "get_jobs", mock_get_jobs)

    rJobs = scrape_jobs("python", pMaxItems=30)

    assert vCalls == [{"tag": "python", "geo": "france", "count": 30}]
    assert len(rJobs) == 30


def test_scrape_jobs_caps_count(monkeypatch):
    """Vérifie que le nombre demandé ne dépasse pas le maximum de l'API."""

    vCalls = []

    def mock_get_jobs(pTag, pGeo, pCount):
        vCalls.append(pCount)

        rJobs = []

        return rJobs

    monkeypatch.setattr(service, "get_jobs", mock_get_jobs)

    rJobs = scrape_jobs("python", pMaxItems=500)

    assert vCalls == [200]
    assert rJobs.empty
