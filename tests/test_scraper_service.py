"""
Tests du service de scraping.
"""

from unittest.mock import patch

from services.scraper_service import scrape_job


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
        "services.scraper_service.fetch_page",
        return_value=html
    ):
        job = scrape_job("https://example.com/job")

    assert job.title == "Développeur Python"
    assert job.company == "Entreprise A"