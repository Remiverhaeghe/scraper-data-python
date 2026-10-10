"""Tests du service Remotive"""

from datetime import datetime

from job.sources.remotive import service
from job.sources.remotive.service import scrape_jobs

NOW = datetime(2026, 10, 10, 12, 0, 0)


def build_job(pId, pPublicationDate):
    """Construit une offre Remotive minimale."""

    rJob = {"id": pId, "publication_date": pPublicationDate}

    return rJob


def test_scrape_jobs_respects_publication_delay(monkeypatch):
    """Vérifie que les offres de moins de 24 heures sont écartées."""

    vJobs = [
        build_job(1, "2026-10-09T11:00:00"),
        build_job(2, "2026-10-09T13:00:00"),
        build_job(3, "date invalide"),
    ]

    monkeypatch.setattr(service, "get_jobs", lambda pSearch, pLimit: vJobs)

    rJobs = scrape_jobs("python", pNow=NOW)

    assert rJobs["source_id"].tolist() == ["1"]


def test_scrape_jobs_applies_max_items(monkeypatch):
    """Vérifie la limitation du nombre d'offres."""

    vJobs = [build_job(vId, "2026-10-01T10:00:00") for vId in range(5)]

    monkeypatch.setattr(service, "get_jobs", lambda pSearch, pLimit: vJobs)

    rJobs = scrape_jobs("python", pMaxItems=2, pNow=NOW)

    assert len(rJobs) == 2


def test_scrape_jobs_limits_request_without_search(monkeypatch):
    """Vérifie qu'une recherche sans mot-clé ne demande pas toutes les offres."""

    vCalls = []

    def mock_get_jobs(pSearch, pLimit):
        vCalls.append({"search": pSearch, "limit": pLimit})

        rJobs = []

        return rJobs

    monkeypatch.setattr(service, "get_jobs", mock_get_jobs)

    rJobs = scrape_jobs(None, pNow=NOW)

    assert vCalls == [{"search": None, "limit": service.DEFAULT_LIMIT}]
    assert rJobs.empty
