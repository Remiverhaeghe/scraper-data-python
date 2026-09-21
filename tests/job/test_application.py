# ============================================================================
# Tests de l'orchestration du traitement des offres d'emploi
# ============================================================================


from datetime import datetime
from unittest.mock import patch

from job.application import process_jobs
from job.model import Job
from scraper.config import ScrapingConfig
from scraper.result import ScrapingResult


def test_process_jobs():
    """
    Vérifie que le traitement des offres lance le scraping
    et enregistre le résultat dans l'historique.
    """

    vConfig = ScrapingConfig(
        max_items=50,
        delay=1.0,
        timeout=30
    )

    vJobs = [
        Job(
            title="Développeur Python",
            company="Entreprise A",
            location="Lille",
            contract="CDI",
            date="31/08/2026",
            url="https://example.com/job"
        )
    ]

    vScrapingResult = ScrapingResult(
        items=vJobs,
        page_count=1,
        duration_seconds=0.1,
        started_at=datetime(2026, 9, 21, 17, 0, 0)
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

    assert rResult == vScrapingResult
    assert rResult.items == vJobs
    assert rResult.page_count == 1
    assert rResult.duration_seconds >= 0