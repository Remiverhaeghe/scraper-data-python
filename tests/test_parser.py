"""
Tests du parser HTML.
"""

from scraper.parser import parse_html
from scraper.parser import extract_job, parse_html


def test_parse_html():
    """Vérifie la conversion du HTML."""

    html = "<h1>Développeur Python</h1>"

    soup = parse_html(html)

    assert soup.h1.text == "Développeur Python"

def test_extract_job():
    """Vérifie l'extraction d'une offre."""

    html = """
    <h1>Développeur Python</h1>
    <div class="company">OpenAI</div>
    <div class="location">Paris</div>
    <div class="contract">CDI</div>
    <div class="date">31/08/2026</div>
    <a href="https://example.com/job">Voir l'offre</a>
    """

    soup = parse_html(html)
    job = extract_job(soup)

    assert job.title == "Développeur Python"
    assert job.company == "OpenAI"
    assert job.location == "Paris"
    assert job.contract == "CDI"
    assert job.date == "31/08/2026"
    assert job.url == "https://example.com/job"

def test_extract_job_with_missing_data():
    """Vérifie l'extraction d'une offre incomplète."""

    html = """
    <h1>Développeur Python</h1>
    <div class="company">OpenAI</div>
    <div class="location">Paris</div>
    <a href="https://example.com/job">Voir l'offre</a>
    """

    soup = parse_html(html)
    job = extract_job(soup)

    assert job.title == "Développeur Python"
    assert job.company == "OpenAI"
    assert job.location == "Paris"
    assert job.contract == ""
    assert job.date == ""
    assert job.url == "https://example.com/job"