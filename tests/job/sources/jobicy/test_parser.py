"""Tests de la transformation des offres Jobicy"""

from job.csv_schema import JOB_COLUMNS
from job.sources.jobicy.parser import parse_job, parse_jobs


def build_job(**pValues):
    """Construit une offre Jobicy proche d'une réponse réelle."""

    rJob = {
        "id": 152919,
        "url": "https://jobicy.com/jobs/152919-staff-software-engineer-data",
        "jobTitle": "Staff Software Engineer - Data",
        "companyName": "Entreprise A",
        "jobIndustry": ["Software Engineering"],
        "jobType": ["Full-Time"],
        "jobGeo": "Europe,  USA",
        "jobLevel": "Senior",
        "jobDescription": "<p>Build <strong>data</strong> pipelines</p>",
        "pubDate": "2026-10-10T03:23:28+00:00",
        "salaryMin": 100000,
        "salaryMax": 155000,
        "salaryCurrency": "EUR",
        "salaryPeriod": "yearly",
    }

    rJob.update(pValues)

    return rJob


def test_parse_job():
    """Vérifie la transformation d'une offre Jobicy."""

    rJob = parse_job(build_job())

    assert rJob["source"] == "jobicy"
    assert rJob["source_id"] == "152919"
    assert rJob["url"] == "https://jobicy.com/jobs/152919-staff-software-engineer-data"
    assert rJob["location"] == "Europe, USA"
    assert rJob["contract_type"] == "Full-Time"
    assert rJob["employment_type"] == "full_time"
    assert rJob["salary_min"] == 100000
    assert rJob["salary_currency"] == "EUR"
    assert rJob["salary_period"] == "year"
    assert rJob["description"] == "Build data pipelines"
    assert rJob["experience_level"] == "Senior"
    assert rJob["job_type"] == "Software Engineering"


def test_parse_job_without_salary():
    """Vérifie une offre sans salaire et au type de poste ambigu."""

    rJob = parse_job(
        build_job(
            jobType=["Contract"],
            salaryMin=None,
            salaryMax=None,
            salaryCurrency=None,
            salaryPeriod=None,
        )
    )

    assert rJob["contract"] is None
    assert rJob["contract_type"] == "Contract"
    assert rJob["employment_type"] is None
    assert rJob["salary_period"] is None


def test_parse_jobs():
    """Vérifie la création d'un DataFrame au format commun."""

    rJobs = parse_jobs([build_job(), build_job(id=2)])

    assert list(rJobs.columns) == JOB_COLUMNS
    assert rJobs["source_id"].tolist() == ["152919", "2"]
