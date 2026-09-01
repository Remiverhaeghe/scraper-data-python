"""
Tests du parser HTML.
"""

from job.model import Job
from job.parser import extract_job, extract_jobs, parse_html


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

def test_extract_jobs():
    """Vérifie l'extraction de plusieurs offres."""

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

    <div class="job">
        <h1>Développeur Web</h1>
        <div class="company">Entreprise C</div>
        <div class="location">Lyon</div>
        <div class="contract">CDI</div>
        <div class="date">29/08/2026</div>
        <a href="https://example.com/job-3">Voir l'offre</a>
    </div>
    """

    soup = parse_html(html)
    jobs = extract_jobs(soup)

    assert len(jobs) == 3
    assert jobs[0].title == "Développeur Python"
    assert jobs[1].title == "Développeur Java"
    assert jobs[2].title == "Développeur Web"