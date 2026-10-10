"""Tests de l'orchestration du traitement des offres d'emploi"""

from datetime import datetime
from unittest.mock import patch

import pandas as pd
import pytest

from job.application import build_search_parameters, process_jobs
from job.config import JobScrapingConfig
from job.sources.aggregator import ScrapingCancelled
from job.sources.config import SourceConfig
from scraper.result import ScrapingResult

# Réglages simulés : un test ne doit jamais lire la vraie base de l'application
SETTINGS = {
    "net_salary_percent": 80,
    "income_tax_rate": 7.5,
    "new_offer_days": 3,
    "follow_up_days": 7,
}


def test_process_jobs():
    """Vérifie que le traitement des offres lance le scraping
    multi-sources, met à jour le suivi des offres,
    enregistre le résultat brut dans l'historique
    et applique les filtres.
    """

    vConfig = JobScrapingConfig(max_items=50, delay=1.0, timeout=30, keyword="Python")

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
                "skills": "Python, Django, Git",
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
                "skills": "Java, Spring, Git",
            },
        ]
    )

    vScrapingResult = ScrapingResult(
        items=vJobs,
        page_count=1,
        duration_seconds=0.1,
        started_at=datetime(2026, 9, 21, 17, 0, 0),
    )

    with patch(
        "job.application.scrape_sources", return_value=vScrapingResult
    ) as vScrapeSources, patch(
        "job.application.save_offers", return_value=vJobs
    ) as vSaveOffers, patch(
        "job.application.record_history"
    ) as vRecordHistory, patch(
        "job.application.load_settings", return_value=SETTINGS
    ):

        rResult = process_jobs(vConfig)

    vScrapeSources.assert_called_once()

    vScrapedConfig = vScrapeSources.call_args.args[0]

    assert vScrapedConfig.keyword == "Python"
    assert vScrapedConfig.net_salary_ratio == 0.8
    assert vScrapedConfig.income_tax_rate == 7.5

    vSaveOffers.assert_called_once()

    vSaveArguments = vSaveOffers.call_args.args

    assert vSaveArguments[0] == "data/scraper.db"

    assert vSaveArguments[1] is vScrapingResult.items

    assert isinstance(vSaveArguments[2], datetime)

    vRecordHistory.assert_called_once()

    vHistoryArguments = vRecordHistory.call_args.args

    assert vHistoryArguments[0] == "data/scraper.db"
    assert vHistoryArguments[1] == "job"
    assert vHistoryArguments[2] == "multi-source"
    assert vHistoryArguments[3].items is vJobs
    assert vRecordHistory.call_args.kwargs["pParameters"] == {
        "keyword": "Python",
        "sources": [],
    }

    assert rResult is not vScrapingResult

    assert len(rResult.items) == 1

    assert rResult.items.iloc[0]["title"] == ("Développeur Python")

    assert rResult.items.iloc[0]["url"] == ("https://example.com/job-1")

    assert len(vScrapingResult.items) == 2

    assert rResult.page_count == 1

    assert rResult.duration_seconds >= 0


def test_process_jobs_saves_nothing_when_cancelled():
    """Vérifie qu'un arrêt pendant le scraping n'enregistre rien."""

    with patch(
        "job.application.scrape_sources", side_effect=ScrapingCancelled()
    ), patch("job.application.save_offers") as vSaveOffers, patch(
        "job.application.record_history"
    ) as vRecordHistory, patch(
        "job.application.load_settings", return_value=SETTINGS
    ):

        with pytest.raises(ScrapingCancelled):
            process_jobs(JobScrapingConfig())

    vSaveOffers.assert_not_called()

    vRecordHistory.assert_not_called()


def test_build_search_parameters_keeps_filled_criteria():
    """Vérifie que seuls les critères renseignés et les sources actives sont gardés."""

    vConfig = JobScrapingConfig(location="Lille", contract="CDI", remote=True)

    vConfig.sources["adzuna"] = SourceConfig(enabled=True)
    vConfig.sources["jooble"] = SourceConfig(enabled=False)

    assert build_search_parameters(vConfig) == {
        "location": "Lille",
        "contract": "CDI",
        "remote": True,
        "sources": ["adzuna"],
    }
