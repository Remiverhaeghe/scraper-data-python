# ============================================================================
# Tests du service de scraping des offres d'emploi
# ============================================================================

import pytest

from unittest.mock import patch

from job.model import Job
from job.service import scrape_job, scrape_jobs
from scraper.config import ScrapingConfig


def test_scrape_job():
    """
    Vérifie la récupération d'une offre.
    """

    vConfig = ScrapingConfig(
        timeout=30
    )

    vHtml = """
    <div class="job">
        <h1>Développeur Python</h1>
        <div class="company">Entreprise A</div>
        <div class="location">Paris</div>
        <div class="contract">CDI</div>
        <div class="date">31/08/2026</div>
        <a href="https://example.com/job">Voir l'offre</a>
    </div>
    """

    with patch(
        "job.service.fetch_page",
        return_value=vHtml
    ) as vFetchPage:

        vJob = scrape_job(
            "https://example.com/job",
            vConfig
        )

    vFetchPage.assert_called_once_with(
        "https://example.com/job",
        vConfig
    )

    assert isinstance(vJob, Job)
    assert vJob.title == "Développeur Python"
    assert vJob.company == "Entreprise A"


def test_scrape_jobs():
    """
    Vérifie la récupération de plusieurs offres.
    """

    vConfig = ScrapingConfig(
        timeout=30
    )

    vHtml = """
    <div class="job">
        <h1>Développeur Python</h1>
        <div class="company">Entreprise A</div>
        <div class="location">Paris</div>
        <div class="contract">CDI</div>
        <div class="date">31/08/2026</div>
        <a href="https://example.com/job-1">Voir l'offre</a>
    </div>

    <div class="job">
        <h1>Développeur Java</h1>
        <div class="company">Entreprise B</div>
        <div class="location">Lille</div>
        <div class="contract">CDD</div>
        <div class="date">30/08/2026</div>
        <a href="https://example.com/job-2">Voir l'offre</a>
    </div>
    """

    with patch(
        "job.service.fetch_page",
        return_value=vHtml
    ) as vFetchPage:

        vJobs = scrape_jobs(
            "https://example.com/jobs",
            vConfig
        )

    vFetchPage.assert_called_once_with(
        "https://example.com/jobs",
        vConfig
    )

    assert len(vJobs) == 2
    assert vJobs[0].title == "Développeur Python"
    assert vJobs[1].title == "Développeur Java"


def test_scrape_jobs_propagates_fetch_error():
    """
    Vérifie qu'une erreur de récupération est propagée.
    """

    vConfig = ScrapingConfig(
        timeout=30
    )

    with patch(
        "job.service.fetch_page",
        side_effect=RuntimeError("Erreur HTTP")
    ):

        try:
            scrape_jobs(
                "https://example.com/jobs",
                vConfig
            )
            assert False
        except RuntimeError as vError:
            assert str(vError) == "Erreur HTTP"

def test_scrape_jobs_propagates_fetch_error():
    """
    Vérifie qu'une erreur de récupération est propagée.
    """

    vConfig = ScrapingConfig(
        timeout=30
    )

    with patch(
        "job.service.fetch_page",
        side_effect=RuntimeError("Erreur HTTP")
    ):

        with pytest.raises(
            RuntimeError,
            match="Erreur HTTP"
        ):
            scrape_jobs(
                "https://example.com/jobs",
                vConfig
            )