"""Tests de la transformation des offres Arbeitnow"""

from job.csv_schema import JOB_COLUMNS
from job.sources.arbeitnow.parser import parse_job, parse_jobs


def build_job(**pValues):
    """Construit une offre Arbeitnow proche d'une réponse réelle."""

    rJob = {
        "slug": "python-developer-berlin-222230",
        "company_name": "Entreprise A",
        "title": "Python Developer",
        "description": "<h2>Über uns</h2><p>Wir suchen</p>",
        "remote": False,
        "url": "https://www.arbeitnow.com/jobs/companies/a/python-developer",
        "tags": ["Software Development"],
        "job_types": ["Full-time permanent", "Mid-senior"],
        "location": "Berlin",
        "created_at": 1791622873,
    }

    rJob.update(pValues)

    return rJob


def test_parse_job():
    """Vérifie la transformation d'une offre Arbeitnow."""

    rJob = parse_job(build_job())

    assert rJob["source"] == "arbeitnow"
    assert rJob["source_id"] == "python-developer-berlin-222230"
    assert rJob["company"] == "Entreprise A"
    assert rJob["location"] == "Berlin"
    assert rJob["remote"] is False
    assert rJob["remote_type"] is None
    assert rJob["contract"] is None
    assert rJob["contract_type"] == "Full-time permanent, Mid-senior"
    assert rJob["description"] == "Über uns Wir suchen"
    assert rJob["published_at"] == "2026-10-10T09:01:13+00:00"


def test_parse_job_remote_without_location():
    """Vérifie une offre en télétravail sans localisation."""

    rJob = parse_job(build_job(remote=True, location="", job_types=[]))

    assert rJob["remote_type"] == "full"
    assert rJob["location"] is None
    assert rJob["contract_type"] is None


def test_parse_jobs():
    """Vérifie la création d'un DataFrame au format commun."""

    rJobs = parse_jobs([build_job(), build_job(slug="autre")])

    assert list(rJobs.columns) == JOB_COLUMNS
    assert rJobs["source_id"].tolist() == ["python-developer-berlin-222230", "autre"]
