# ============================================================================
# Tests de l'orchestration du traitement des offres d'emploi
# ============================================================================


from datetime import datetime
from unittest.mock import patch

import pandas as pd

from job.application import process_jobs
from job.config import JobScrapingConfig
from scraper.result import ScrapingResult


def test_process_jobs():
    """
    Vérifie que le traitement des offres lance le scraping,
    enregistre le résultat brut dans l'historique et applique
    les filtres.
    """

    vConfig = JobScrapingConfig(
        max_items=50,
        delay=1.0,
        timeout=30,
        keyword="Python"
    )

    vJobs = pd.DataFrame(
        [
            {
                "title": "Développeur Python",
                "company": "Entreprise A",
                "location": "Lille",
                "city": "Lille",
                "postal_code": "59000",
                "distance_km": 10,
                "contract": "CDI",
                "salary_min": 40000,
                "salary_max": 50000,
                "salary_period": "year",
                "remote": True,
                "remote_days": 2,
                "remote_type": "hybrid",
                "nearest_metro": "République",
                "metro_distance_km": 0.5,
                "date": "31/08/2026",
                "url": "https://example.com/job-1",
                "description": "Développement Python",
                "missions": "Développer des applications Python",
                "requirements": "Expérience Python",
                "education": "Bac+3",
                "skills": "Python, Django, Git"
            },
            {
                "title": "Développeur Java",
                "company": "Entreprise B",
                "location": "Lille",
                "city": "Lille",
                "postal_code": "59000",
                "distance_km": 10,
                "contract": "CDI",
                "salary_min": 40000,
                "salary_max": 50000,
                "salary_period": "year",
                "remote": True,
                "remote_days": 2,
                "remote_type": "hybrid",
                "nearest_metro": "République",
                "metro_distance_km": 0.5,
                "date": "31/08/2026",
                "url": "https://example.com/job-2",
                "description": "Développement Java",
                "missions": "Développer des applications Java",
                "requirements": "Expérience Java",
                "education": "Bac+3",
                "skills": "Java, Spring, Git"
            }
        ]
    )

    vScrapingResult = ScrapingResult(
        items=vJobs,
        page_count=1,
        duration_seconds=0.1,
        started_at=datetime(
            2026,
            9,
            21,
            17,
            0,
            0
        )
    )

    with patch(
        "job.application.scrape_jobs",
        return_value=vScrapingResult
    ) as vScrapeJobs, patch(
        "job.application.record_history"
    ) as vRecordHistory:

        rResult = process_jobs(
            "https://example.com/jobs",
            vConfig
        )

    vScrapeJobs.assert_called_once_with(
        "https://example.com/jobs",
        vConfig
    )

    vRecordHistory.assert_called_once_with(
        "data/scraper.db",
        "job",
        "https://example.com/jobs",
        vScrapingResult
    )

    assert rResult is not vScrapingResult

    assert len(rResult.items) == 1

    assert rResult.items.iloc[0]["title"] == (
        "Développeur Python"
    )

    assert rResult.items.iloc[0]["url"] == (
        "https://example.com/job-1"
    )

    assert len(vScrapingResult.items) == 2

    assert rResult.page_count == 1

    assert rResult.duration_seconds >= 0