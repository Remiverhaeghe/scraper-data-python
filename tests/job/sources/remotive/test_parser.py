"""Tests de la transformation des offres Remotive"""

from job.csv_schema import JOB_COLUMNS
from job.sources.remotive.parser import parse_job, parse_jobs


def build_job(**pValues):
    """Construit une offre Remotive proche d'une réponse réelle."""

    rJob = {
        "id": 2091045,
        "url": "https://remotive.com/remote-jobs/software-dev/python-2091045",
        "title": "Senior Python Developer",
        "company_name": "Entreprise A",
        "category": "Software Development",
        "tags": ["python", "django"],
        "job_type": "full_time",
        "publication_date": "2026-10-07T01:11:09",
        "candidate_required_location": "Europe",
        "salary": "$90k - $105k",
        "description": "<p>Build <b>APIs</b> in Python</p>",
    }

    rJob.update(pValues)

    return rJob


def test_parse_job():
    """Vérifie la transformation d'une offre Remotive."""

    rJob = parse_job(build_job())

    assert rJob["source"] == "remotive"
    assert rJob["source_id"] == "2091045"
    assert rJob["company"] == "Entreprise A"
    assert rJob["url"] == "https://remotive.com/remote-jobs/software-dev/python-2091045"
    assert rJob["location"] == "Europe"
    assert rJob["remote"] is True
    assert rJob["employment_type"] == "full_time"
    assert rJob["contract"] is None
    assert rJob["salary_label"] == "$90k - $105k"
    assert rJob["salary_min"] is None
    assert rJob["description"] == "Build APIs in Python"
    assert rJob["skills"] == ["python", "django"]
    assert rJob["job_type"] == "Software Development"


def test_parse_job_freelance():
    """Vérifie qu'une mission freelance est qualifiée comme telle."""

    rJob = parse_job(build_job(job_type="freelance", salary=""))

    assert rJob["contract"] == "FREELANCE"
    assert rJob["employment_type"] is None
    assert rJob["salary_label"] is None


def test_parse_jobs():
    """Vérifie la création d'un DataFrame au format commun."""

    rJobs = parse_jobs([build_job(), build_job(id=2)])

    assert list(rJobs.columns) == JOB_COLUMNS
    assert rJobs["source_id"].tolist() == ["2091045", "2"]
