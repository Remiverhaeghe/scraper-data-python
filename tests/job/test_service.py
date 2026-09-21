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

        vResult = scrape_jobs(
            "https://example.com/jobs",
            vConfig
        )

    vFetchPage.assert_called_once_with(
        "https://example.com/jobs",
        vConfig
    )

    assert len(vResult.items) == 2
    assert vResult.items[0].title == "Développeur Python"
    assert vResult.items[1].title == "Développeur Java"

    assert vResult.page_count == 1
    assert vResult.duration_seconds >= 0


def test_scrape_jobs_with_multiple_pages():
    """
    Vérifie que plusieurs pages d'offres sont parcourues.
    """

    vConfig = ScrapingConfig(
        timeout=30,
        max_pages=2
    )

    vJob1 = Job(
        title="Développeur Python",
        company="Entreprise A",
        location="Paris",
        contract="CDI",
        date="31/08/2026",
        url="https://example.com/job-1"
    )

    vJob2 = Job(
        title="Développeur Java",
        company="Entreprise B",
        location="Lille",
        contract="CDD",
        date="30/08/2026",
        url="https://example.com/job-2"
    )

    vSoup1 = object()
    vSoup2 = object()

    with patch(
        "job.service.fetch_page",
        side_effect=[
            "<html>Page 1</html>",
            "<html>Page 2</html>"
        ]
    ) as vFetchPage, patch(
        "job.service.parse_html",
        side_effect=[
            vSoup1,
            vSoup2
        ]
    ), patch(
        "job.service.extract_jobs",
        side_effect=[
            [vJob1],
            [vJob2]
        ]
    ), patch(
        "job.service.extract_next_url",
        side_effect=[
            "https://example.com/jobs?page=2",
            ""
        ]
    ):

        vResult = scrape_jobs(
            "https://example.com/jobs",
            vConfig
        )

    assert vResult.items == [
        vJob1,
        vJob2
    ]

    assert vResult.page_count == 2
    assert vResult.duration_seconds >= 0

    assert vFetchPage.call_count == 2


def test_scrape_jobs_respects_max_items():
    """
    Vérifie que le nombre maximum d'offres est respecté.
    """

    vConfig = ScrapingConfig(
        timeout=30,
        max_items=1
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
    ):

        vResult = scrape_jobs(
            "https://example.com/jobs",
            vConfig
        )

    assert len(vResult.items) == 1
    assert vResult.items[0].title == "Développeur Python"

    assert vResult.page_count == 1
    assert vResult.duration_seconds >= 0


def test_scrape_jobs_keeps_all_jobs_when_max_items_is_greater():
    """
    Vérifie que toutes les offres sont conservées lorsque la limite
    est supérieure au nombre d'offres récupérées.
    """

    vConfig = ScrapingConfig(
        timeout=30,
        max_items=5
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
    ):

        vResult = scrape_jobs(
            "https://example.com/jobs",
            vConfig
        )

    assert len(vResult.items) == 2
    assert vResult.page_count == 1
    assert vResult.duration_seconds >= 0


def test_scrape_jobs_keeps_all_jobs_when_max_items_is_equal():
    """
    Vérifie que toutes les offres sont conservées lorsque la limite
    correspond exactement au nombre d'offres récupérées.
    """

    vConfig = ScrapingConfig(
        timeout=30,
        max_items=2
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
    ):

        vResult = scrape_jobs(
            "https://example.com/jobs",
            vConfig
        )

    assert len(vResult.items) == 2
    assert vResult.page_count == 1
    assert vResult.duration_seconds >= 0


def test_scrape_jobs_returns_error_result_when_fetch_fails():
    """
    Vérifie qu'une erreur de récupération est enregistrée
    dans le résultat du scraping.
    """

    vConfig = ScrapingConfig(
        timeout=30
    )

    with patch(
        "job.service.fetch_page",
        side_effect=RuntimeError("Erreur HTTP")
    ):

        vResult = scrape_jobs(
            "https://example.com/jobs",
            vConfig
        )

    assert vResult.items == []
    assert vResult.page_count == 1
    assert vResult.duration_seconds >= 0
    assert vResult.started_at is not None
    assert vResult.status == "error"
    assert vResult.error_message == "Erreur HTTP"