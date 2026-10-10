"""Tests de la transformation des offres Jooble"""

from job.csv_schema import JOB_COLUMNS
from job.sources.jooble.parser import parse_job, parse_jobs


def build_job(**pValues):
    """Construit une offre Jooble au format documenté."""

    rJob = {
        "id": -1234567890,
        "title": "Développeur <b>Python</b> H/F",
        "location": "Lille",
        "snippet": "&nbsp;...missions <b>Python</b> et Django...&nbsp;",
        "salary": "40 000 € par an",
        "source": "hellowork.com",
        "type": "CDI",
        "link": "https://fr.jooble.org/desc/-1234567890",
        "company": "Entreprise A",
        "updated": "2026-10-09T00:00:00.0000000",
    }

    rJob.update(pValues)

    return rJob


def test_parse_job():
    """Vérifie la transformation d'une offre Jooble."""

    rJob = parse_job(build_job())

    assert rJob["source"] == "jooble"
    assert rJob["source_id"] == "-1234567890"
    assert rJob["title"] == "Développeur Python H/F"
    assert rJob["url"] == "https://fr.jooble.org/desc/-1234567890"
    assert rJob["contract_type"] == "CDI"
    assert rJob["salary_label"] == "40 000 € par an"
    assert rJob["description"] == "...missions Python et Django..."
    assert rJob["job_type"] == "hellowork.com"


def test_parse_job_with_empty_values():
    """Vérifie que les champs vides fournis par Jooble deviennent vides."""

    rJob = parse_job(build_job(company="", salary="", type=""))

    assert rJob["company"] is None
    assert rJob["salary_label"] is None
    assert rJob["contract_type"] is None


def test_parse_jobs():
    """Vérifie la création d'un DataFrame au format commun."""

    rJobs = parse_jobs([build_job(), build_job(id=2)])

    assert list(rJobs.columns) == JOB_COLUMNS
    assert rJobs["source_id"].tolist() == ["-1234567890", "2"]
