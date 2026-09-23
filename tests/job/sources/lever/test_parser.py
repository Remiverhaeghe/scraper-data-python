# ============================================================================
# Tests du parser des offres Lever
# ============================================================================

from job.csv_schema import JOB_COLUMNS
from job.sources.lever.parser import parse_job, parse_jobs


def test_parse_job():
    """
    Vérifie la transformation d'une offre Lever.
    """

    vJob = {
        "id": "job-123",
        "text": "Python Developer",
        "company": "Example Company",
        "country": "FR",
        "hostedUrl": "https://jobs.example.com/job-123",
        "createdAt": 1234567890000,
        "descriptionPlain": "Développement Python",
        "categories": {
            "location": "Paris",
            "commitment": "Full-time",
            "department": "Engineering",
            "level": "Mid Level",
            "team": "Software"
        }
    }

    rJob = parse_job(vJob)

    assert rJob["title"] == "Python Developer"
    assert rJob["company"] == "Example Company"
    assert rJob["source"] == "lever"
    assert rJob["source_id"] == "job-123"
    assert rJob["url"] == "https://jobs.example.com/job-123"

    assert rJob["location"] == "Paris"
    assert rJob["country"] == "FR"

    assert rJob["contract"] == "Full-time"
    assert rJob["employment_type"] == "Full-time"

    assert rJob["date"] == 1234567890000
    assert rJob["published_at"] == 1234567890000

    assert rJob["description"] == "Développement Python"

    assert rJob["department"] == "Engineering"
    assert rJob["experience_level"] == "Mid Level"
    assert rJob["job_type"] == "Software"


def test_parse_job_without_optional_values():
    """
    Vérifie qu'une offre incomplète est correctement traitée.
    """

    vJob = {
        "id": "job-123",
        "text": "Python Developer",
        "categories": {}
    }

    rJob = parse_job(vJob)

    assert rJob["title"] == "Python Developer"
    assert rJob["source"] == "lever"
    assert rJob["source_id"] == "job-123"

    assert rJob["company"] is None
    assert rJob["location"] is None
    assert rJob["country"] is None
    assert rJob["salary_min"] is None
    assert rJob["salary_max"] is None


def test_parse_jobs():
    """
    Vérifie la transformation de plusieurs offres Lever.
    """

    vJobs = [
        {
            "id": "job-1",
            "text": "Python Developer",
            "country": "FR",
            "categories": {
                "location": "Paris"
            }
        },
        {
            "id": "job-2",
            "text": "Java Developer",
            "country": "FR",
            "categories": {
                "location": "Lille"
            }
        }
    ]

    rData = parse_jobs(vJobs)

    assert len(rData) == 2
    assert list(rData.columns) == JOB_COLUMNS

    assert rData.iloc[0]["title"] == "Python Developer"
    assert rData.iloc[1]["title"] == "Java Developer"

    assert rData.iloc[0]["source"] == "lever"
    assert rData.iloc[1]["source"] == "lever"


def test_parse_jobs_without_results():
    """
    Vérifie qu'une liste vide produit un DataFrame vide mais structuré.
    """

    rData = parse_jobs([])

    assert rData.empty
    assert list(rData.columns) == JOB_COLUMNS