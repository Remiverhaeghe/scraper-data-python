"""Tests de la transformation des offres Findwork"""

from job.csv_schema import JOB_COLUMNS
import pytest

from job.sources.findwork.parser import guess_title, parse_job, parse_jobs


def build_job(**pValues):
    """Construit une offre Findwork au format documenté."""

    rJob = {
        "id": 12345,
        "role": "Backend Python Developer",
        "company_name": "Entreprise A",
        "employment_type": "full time",
        "location": "Paris, France",
        "remote": True,
        "url": "https://findwork.dev/12345/backend-python-developer",
        "text": "<p>Build <b>APIs</b></p>",
        "date_posted": "2026-10-08T10:00:00Z",
        "keywords": ["python", "django"],
        "source": "Remotive",
    }

    rJob.update(pValues)

    return rJob


def test_parse_job():
    """Vérifie la transformation d'une offre Findwork."""

    rJob = parse_job(build_job())

    assert rJob["source"] == "findwork"
    assert rJob["source_id"] == "12345"
    assert rJob["title"] == "Backend Python Developer"
    assert rJob["location"] == "Paris, France"
    assert rJob["remote"] is True
    assert rJob["remote_type"] == "full"
    assert rJob["contract_type"] == "full time"
    assert rJob["description"] == "Build APIs"
    assert rJob["skills"] == ["python", "django"]
    assert rJob["job_type"] == "Remotive"


def test_parse_job_onsite():
    """Vérifie une offre sur site, sans type de poste."""

    rJob = parse_job(build_job(remote=False, employment_type=None))

    assert rJob["remote_type"] is None
    assert rJob["contract_type"] is None


def test_parse_jobs():
    """Vérifie la création d'un DataFrame au format commun."""

    rJobs = parse_jobs([build_job(), build_job(id=2)])

    assert list(rJobs.columns) == JOB_COLUMNS
    assert rJobs["source_id"].tolist() == ["12345", "2"]


@pytest.mark.parametrize(
    "pText, pTitle",
    [
        (
            "Currently hiring BI Analyst and Network Specialist\nDétails",
            "Currently hiring BI Analyst and Network Specialist",
        ),
        ("Remote: Yes Willing to relocate: No", None),
        ("- Engineering Manager : you will lead", None),
        ("x" * 100, None),
        (None, None),
    ],
)
def test_guess_title_from_first_line(pText, pTitle):
    """Vérifie le titre tiré de la première ligne quand le poste manque."""

    assert guess_title(pText) == pTitle
