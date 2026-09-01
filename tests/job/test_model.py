"""
Tests du modèle Job.
"""

from job.model import Job


def test_job():
    """Vérifie la création d'une offre."""

    job = Job(
        title="Développeur Python",
        company="Entreprise A",
        location="Paris",
        contract="CDI",
        date="31/08/2026",
        url="https://example.com/job"
    )

    assert job.title == "Développeur Python"
    assert job.company == "Entreprise A"
    assert job.location == "Paris"
    assert job.contract == "CDI"
    assert job.date == "31/08/2026"
    assert job.url == "https://example.com/job"