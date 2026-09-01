"""
Tests du service de scraping.
"""

from unittest.mock import patch

from job.service import scrape_job, scrape_jobs


def test_scrape_job():
    """Vérifie la récupération d'une offre."""

    html = """
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
        return_value=html
    ):
        job = scrape_job("https://example.com/job")

    assert job.title == "Développeur Python"
    assert job.company == "Entreprise A"


def test_scrape_jobs():
    """Vérifie la récupération de plusieurs offres."""

    html = """
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
        return_value=html
    ):
        jobs = scrape_jobs("https://example.com/jobs")

    assert len(jobs) == 2
    assert jobs[0].title == "Développeur Python"
    assert jobs[1].title == "Développeur Java"