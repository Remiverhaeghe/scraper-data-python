# ============================================================================
# Tests du service de scraping Lever
# ============================================================================

import pandas as pd

from job.sources.lever.service import scrape_jobs


def test_scrape_jobs(monkeypatch):
    """
    Vérifie le scraping de plusieurs pages Lever.
    """

    vJobsPage1 = [
        {
            "id": "job-1",
            "text": "Python Developer"
        },
        {
            "id": "job-2",
            "text": "Java Developer"
        }
    ]

    vJobsPage2 = [
        {
            "id": "job-3",
            "text": "DevOps Engineer"
        }
    ]

    vCalls = []

    def mock_get_jobs(
        pSite,
        pLimit=100,
        pSkip=0
    ):
        vCalls.append(
            {
                "site": pSite,
                "limit": pLimit,
                "skip": pSkip
            }
        )

        if pSkip == 0:
            return vJobsPage1

        return vJobsPage2

    monkeypatch.setattr(
        "job.sources.lever.service.get_jobs",
        mock_get_jobs
    )

    rData = scrape_jobs(
        "example-company",
        pLimit=2
    )

    assert isinstance(rData, pd.DataFrame)
    assert len(rData) == 3

    assert list(rData["source"]) == [
        "lever",
        "lever",
        "lever"
    ]

    assert vCalls == [
        {
            "site": "example-company",
            "limit": 2,
            "skip": 0
        },
        {
            "site": "example-company",
            "limit": 2,
            "skip": 2
        }
    ]


def test_scrape_jobs_without_results(monkeypatch):
    """
    Vérifie le comportement lorsqu'aucune offre n'est disponible.
    """

    def mock_get_jobs(
        pSite,
        pLimit=100,
        pSkip=0
    ):
        return []

    monkeypatch.setattr(
        "job.sources.lever.service.get_jobs",
        mock_get_jobs
    )

    rData = scrape_jobs(
        "example-company"
    )

    assert isinstance(rData, pd.DataFrame)
    assert rData.empty


def test_scrape_jobs_single_page(monkeypatch):
    """
    Vérifie qu'une seule page est demandée lorsque le nombre
    d'offres est inférieur à la limite.
    """

    vJobs = [
        {
            "id": "job-1",
            "text": "Python Developer"
        }
    ]

    vCalls = []

    def mock_get_jobs(
        pSite,
        pLimit=100,
        pSkip=0
    ):
        vCalls.append(pSkip)
        return vJobs

    monkeypatch.setattr(
        "job.sources.lever.service.get_jobs",
        mock_get_jobs
    )

    rData = scrape_jobs(
        "example-company",
        pLimit=100
    )

    assert len(rData) == 1
    assert vCalls == [0]