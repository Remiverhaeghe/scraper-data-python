# ============================================================================
# Tests du parser HTML des offres d'emploi
# ============================================================================


from job.model import Job
from job.parser import (
    extract_job,
    extract_jobs,
    parse_html
)


def test_parse_html():
    """
    Vérifie la conversion du HTML en objet BeautifulSoup.
    """

    vHtml = "<h1>Développeur Python</h1>"

    vSoup = parse_html(
        vHtml
    )

    assert vSoup.h1.text == "Développeur Python"


def test_extract_job():
    """
    Vérifie l'extraction d'une offre.
    """

    vHtml = """
    <h1>Développeur Python</h1>
    <div class="company">OpenAI</div>
    <div class="location">Paris</div>
    <div class="contract">CDI</div>
    <div class="date">31/08/2026</div>
    <a href="https://example.com/job">Voir l'offre</a>
    """

    vSoup = parse_html(
        vHtml
    )

    vJob = extract_job(
        vSoup
    )

    assert isinstance(vJob, Job)
    assert vJob.title == "Développeur Python"
    assert vJob.company == "OpenAI"
    assert vJob.location == "Paris"
    assert vJob.contract == "CDI"
    assert vJob.date == "31/08/2026"
    assert vJob.url == "https://example.com/job"


def test_extract_job_with_missing_data():
    """
    Vérifie l'extraction d'une offre incomplète.
    """

    vHtml = """
    <h1>Développeur Python</h1>
    <div class="company">OpenAI</div>
    <div class="location">Paris</div>
    <a href="https://example.com/job">Voir l'offre</a>
    """

    vSoup = parse_html(
        vHtml
    )

    vJob = extract_job(
        vSoup
    )

    assert vJob.title == "Développeur Python"
    assert vJob.company == "OpenAI"
    assert vJob.location == "Paris"
    assert vJob.contract == ""
    assert vJob.date == ""
    assert vJob.url == "https://example.com/job"


def test_extract_jobs():
    """
    Vérifie l'extraction de plusieurs offres.
    """

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

    <div class="job">
        <h1>Développeur Web</h1>
        <div class="company">Entreprise C</div>
        <div class="location">Lyon</div>
        <div class="contract">CDI</div>
        <div class="date">29/08/2026</div>
        <a href="https://example.com/job-3">Voir l'offre</a>
    </div>
    """

    vSoup = parse_html(
        vHtml
    )

    vJobs = extract_jobs(
        vSoup
    )

    assert len(vJobs) == 3
    assert vJobs[0].title == "Développeur Python"
    assert vJobs[1].title == "Développeur Java"
    assert vJobs[2].title == "Développeur Web"

def test_extract_job_without_link():
    """
    Vérifie l'extraction d'une offre sans lien.
    """

    vHtml = """
    <h1>Développeur Python</h1>
    <div class="company">OpenAI</div>
    <div class="location">Paris</div>
    <div class="contract">CDI</div>
    <div class="date">31/08/2026</div>
    """

    vSoup = parse_html(
        vHtml
    )

    vJob = extract_job(
        vSoup
    )

    assert vJob.title == "Développeur Python"
    assert vJob.company == "OpenAI"
    assert vJob.location == "Paris"
    assert vJob.contract == "CDI"
    assert vJob.date == "31/08/2026"
    assert vJob.url == ""