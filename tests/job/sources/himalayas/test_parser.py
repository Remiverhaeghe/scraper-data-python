"""Tests de la transformation des offres Himalayas"""

from job.csv_schema import JOB_COLUMNS
from job.sources.himalayas.parser import format_location, parse_job, parse_jobs

GUID = "https://himalayas.app/companies/lemon-io/jobs/senior-python-developer"


def build_job(**pValues):
    """Construit une offre Himalayas proche d'une réponse réelle."""

    rJob = {
        "title": "Senior Python Developer",
        "companyName": "lemon.io",
        "companySlug": "lemon-io",
        "employmentType": "Full Time",
        "minSalary": 60000,
        "maxSalary": 80000,
        "salaryPeriod": "annual",
        "seniority": ["Senior"],
        "currency": "EUR",
        "locationRestrictions": ["France", "Belgium"],
        "categories": ["Python-Developer"],
        "parentCategories": ["Developer"],
        "description": "<p>Python <em>backend</em></p>",
        "pubDate": 1789127040,
        "applicationLink": GUID,
        "guid": GUID,
    }

    rJob.update(pValues)

    return rJob


def test_parse_job():
    """Vérifie la transformation d'une offre Himalayas."""

    rJob = parse_job(build_job())

    assert rJob["source"] == "himalayas"
    assert rJob["source_id"] == GUID
    assert rJob["url"] == GUID
    assert rJob["company_id"] == "lemon-io"
    assert rJob["location"] == "France, Belgium"
    assert rJob["contract"] is None
    assert rJob["employment_type"] == "full_time"
    assert rJob["salary_min"] == 60000
    assert rJob["salary_currency"] == "EUR"
    assert rJob["salary_period"] == "year"
    assert rJob["published_at"] == "2026-09-11T11:44:00+00:00"
    assert rJob["description"] == "Python backend"
    assert rJob["experience_level"] == "Senior"
    assert rJob["job_type"] == "Developer"


def test_parse_job_contractor_is_freelance():
    """Vérifie qu'un poste de contractor est qualifié en freelance."""

    rJob = parse_job(build_job(employmentType="Contractor"))

    assert rJob["contract"] == "FREELANCE"
    assert rJob["employment_type"] is None


def test_format_location_summarizes_long_lists():
    """Vérifie le résumé d'une longue liste de pays."""

    vCountries = ["France", "Belgium", "Spain", "Italy", "Germany", "Austria", "Peru"]

    assert format_location(vCountries) == (
        "France, Belgium, Spain, Italy, Germany (+2 pays)"
    )
    assert format_location([]) is None


def test_parse_jobs():
    """Vérifie la création d'un DataFrame au format commun."""

    rJobs = parse_jobs([build_job(), build_job(guid="autre")])

    assert list(rJobs.columns) == JOB_COLUMNS
    assert rJobs["source_id"].tolist() == [GUID, "autre"]
