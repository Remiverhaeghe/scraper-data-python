# ============================================================================
# Tests de la transformation des offres Greenhouse
# ============================================================================

from job.csv_schema import JOB_COLUMNS
from job.sources.greenhouse.parser import (
    parse_job,
    parse_jobs
)


def test_parse_job():
    """
    Vérifie la transformation d'une offre Greenhouse.
    """

    vJob = {
        "id": 123,
        "title": "Python Developer",
        "company": {
            "name": "Entreprise A"
        },
        "location": {
            "name": "Paris"
        },
        "first_published": "2026-09-22T10:00:00Z",
        "updated_at": "2026-09-22T12:00:00Z",
        "absolute_url": "https://example.com/job/123",
        "content": "<p>Développement Python</p>"
    }

    rJob = parse_job(vJob)

    assert rJob["title"] == "Python Developer"
    assert rJob["company"] == "Entreprise A"
    assert rJob["source"] == "greenhouse"
    assert rJob["source_id"] == "123"
    assert rJob["location"] == "Paris"
    assert rJob["url"] == "https://example.com/job/123"
    assert rJob["description"] == (
        "<p>Développement Python</p>"
    )


def test_parse_job_with_missing_values():
    """
    Vérifie qu'une offre partiellement renseignée est acceptée.
    """

    rJob = parse_job(
        {
            "id": 456,
            "title": "Java Developer"
        }
    )

    assert rJob["title"] == "Java Developer"
    assert rJob["source"] == "greenhouse"
    assert rJob["source_id"] == "456"
    assert rJob["company"] is None
    assert rJob["location"] is None


def test_parse_jobs():
    """
    Vérifie la transformation de plusieurs offres.
    """

    vJobs = [
        {
            "id": 1,
            "title": "Python Developer"
        },
        {
            "id": 2,
            "title": "Java Developer"
        }
    ]

    rDataFrame = parse_jobs(vJobs)

    assert len(rDataFrame) == 2
    assert list(rDataFrame.columns) == JOB_COLUMNS
    assert rDataFrame.iloc[0]["title"] == (
        "Python Developer"
    )
    assert rDataFrame.iloc[1]["title"] == (
        "Java Developer"
    )


def test_parse_empty_jobs():
    """
    Vérifie la transformation d'une liste vide.
    """

    rDataFrame = parse_jobs([])

    assert rDataFrame.empty
    assert list(rDataFrame.columns) == JOB_COLUMNS