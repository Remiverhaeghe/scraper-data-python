# ============================================================================
# Tests du service de scraping des offres d'emploi
# ============================================================================


from unittest.mock import patch

from job.model import Job
from job.service import scrape_job, scrape_jobs


def test_scrape_job():
    """
    Vérifie la récupération d'une offre.
    """

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
    ):
        vJob = scrape_job(
            "https://example.com/job"
        )

    assert isinstance(vJob, Job)
    assert vJob.title == "Développeur Python"
    assert vJob.company == "Entreprise A"


def test_scrape_jobs():
    """
    Vérifie la récupération de plusieurs offres.
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
    """

    with patch(
        "job.service.fetch_page",
        return_value=vHtml
    ):
        vJobs = scrape_jobs(
            "https://example.com/jobs"
        )

    assert len(vJobs) == 2
    assert vJobs[0].title == "Développeur Python"
    assert vJobs[1].title == "Développeur Java"