# ============================================================================
# Tests du parsing et de l'extraction des offres d'emploi
# ============================================================================

from job.model import Job
from job.parser import (
    extract_job,
    extract_jobs,
    extract_next_url,
    parse_html
)


def test_parse_html():
    """
    Vérifie que le HTML est correctement analysé.
    """

    vHtml = "<html><body><h1>Développeur Python</h1></body></html>"

    vSoup = parse_html(vHtml)

    assert vSoup.h1.text == "Développeur Python"


def test_extract_job():
    """
    Vérifie l'extraction d'une offre complète.
    """

    vHtml = """
    <div class="job">
        <h1>Développeur Python</h1>
        <span class="company">Entreprise A</span>
        <span class="location">Paris</span>
        <span class="contract">CDI</span>
        <span class="date">2026-09-20</span>
        <a href="https://example.com/job/1">Voir l'offre</a>
    </div>
    """

    vSoup = parse_html(vHtml)

    vJob = extract_job(
        vSoup
    )

    assert isinstance(vJob, Job)
    assert vJob.title == "Développeur Python"
    assert vJob.company == "Entreprise A"
    assert vJob.location == "Paris"
    assert vJob.contract == "CDI"
    assert vJob.date == "2026-09-20"
    assert vJob.url == "https://example.com/job/1"


def test_extract_job_without_link():
    """
    Vérifie l'extraction d'une offre sans lien.
    """

    vHtml = """
    <div class="job">
        <h1>Développeur Python</h1>
        <span class="company">Entreprise A</span>
    </div>
    """

    vSoup = parse_html(vHtml)

    vJob = extract_job(
        vSoup
    )

    assert vJob.title == "Développeur Python"
    assert vJob.url == ""


def test_extract_job_with_missing_data():
    """
    Vérifie l'extraction d'une offre avec des données absentes.
    """

    vHtml = """
    <div class="job">
        <h1>Développeur Python</h1>
    </div>
    """

    vSoup = parse_html(vHtml)

    vJob = extract_job(
        vSoup
    )

    assert vJob.title == "Développeur Python"
    assert vJob.company == ""
    assert vJob.location == ""
    assert vJob.contract == ""
    assert vJob.date == ""
    assert vJob.url == ""


def test_extract_jobs():
    """
    Vérifie l'extraction de plusieurs offres.
    """

    vHtml = """
    <div class="job">
        <h1>Développeur Python</h1>
        <span class="company">Entreprise A</span>
    </div>

    <div class="job">
        <h1>Développeur Java</h1>
        <span class="company">Entreprise B</span>
    </div>
    """

    vSoup = parse_html(vHtml)

    vJobs = extract_jobs(
        vSoup,
        "https://example.com/jobs"
    )

    assert len(vJobs) == 2
    assert vJobs[0].title == "Développeur Python"
    assert vJobs[1].title == "Développeur Java"


def test_extract_next_url():
    """
    Vérifie l'extraction de l'URL de la page suivante.
    """

    vHtml = """
    <a rel="next" href="https://example.com/jobs?page=2">
        Page suivante
    </a>
    """

    vSoup = parse_html(vHtml)

    vNextUrl = extract_next_url(
        vSoup,
        "https://example.com/jobs"
    )

    assert vNextUrl == "https://example.com/jobs?page=2"


def test_extract_next_url_without_next_page():
    """
    Vérifie qu'une chaîne vide est retournée lorsqu'il n'y a pas
    de page suivante.
    """

    vHtml = """
    <html>
        <body>
            <p>Dernière page</p>
        </body>
    </html>
    """

    vSoup = parse_html(vHtml)

    vNextUrl = extract_next_url(
        vSoup,
        "https://example.com/jobs"
    )

    assert vNextUrl == ""