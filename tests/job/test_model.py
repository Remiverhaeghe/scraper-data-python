# ============================================================================
# Tests du modèle Job
# ============================================================================


from job.model import Job


def test_job():
    """
    Vérifie la création d'une offre avec ses différentes propriétés.
    """

    vJob = Job(
        title="Développeur Python",
        company="Entreprise A",
        location="Paris",
        contract="CDI",
        date="31/08/2026",
        url="https://example.com/job"
    )

    assert vJob.title == "Développeur Python"
    assert vJob.company == "Entreprise A"
    assert vJob.location == "Paris"
    assert vJob.contract == "CDI"
    assert vJob.date == "31/08/2026"
    assert vJob.url == "https://example.com/job"

    assert vJob.city == ""
    assert vJob.postal_code == ""
    assert vJob.distance_km is None
    assert vJob.salary_min is None
    assert vJob.salary_max is None
    assert vJob.salary_period is None
    assert vJob.remote is None
    assert vJob.remote_days is None
    assert vJob.remote_type is None
    assert vJob.nearest_metro is None
    assert vJob.metro_distance_km is None
    assert vJob.description == ""
    assert vJob.missions == ""
    assert vJob.requirements == ""
    assert vJob.education == ""
    assert vJob.skills == ""


def test_job_from_csv_row():
    """
    Vérifie la création d'une offre depuis une ligne CSV.
    """

    vRow = {
        "title": "Développeur Python",
        "company": "Entreprise A",
        "location": "Paris",
        "city": "Paris",
        "postal_code": "75001",
        "distance_km": 2.5,
        "contract": "CDI",
        "salary_min": 40000,
        "salary_max": 50000,
        "salary_period": "year",
        "remote": True,
        "remote_days": 2,
        "remote_type": "hybrid",
        "nearest_metro": "Châtelet",
        "metro_distance_km": 0.5,
        "date": "31/08/2026",
        "url": "https://example.com/job-1",
        "description": "Description de l'offre",
        "missions": "Développer des applications",
        "requirements": "Expérience Python",
        "education": "Bac+3",
        "skills": "Python, Django"
    }

    rJob = Job.from_csv_row(vRow)

    assert isinstance(rJob, Job)
    assert rJob.title == "Développeur Python"
    assert rJob.company == "Entreprise A"
    assert rJob.location == "Paris"
    assert rJob.city == "Paris"
    assert rJob.postal_code == "75001"
    assert rJob.distance_km == 2.5
    assert rJob.contract == "CDI"
    assert rJob.salary_min == 40000
    assert rJob.salary_max == 50000
    assert rJob.salary_period == "year"
    assert rJob.remote is True
    assert rJob.remote_days == 2
    assert rJob.remote_type == "hybrid"
    assert rJob.nearest_metro == "Châtelet"
    assert rJob.metro_distance_km == 0.5
    assert rJob.date == "31/08/2026"
    assert rJob.url == "https://example.com/job-1"
    assert rJob.description == "Description de l'offre"
    assert rJob.missions == "Développer des applications"
    assert rJob.requirements == "Expérience Python"
    assert rJob.education == "Bac+3"
    assert rJob.skills == "Python, Django"


def test_job_to_csv_row():
    """
    Vérifie la conversion d'une offre vers une ligne CSV.
    """

    vJob = Job(
        title="Développeur Python",
        company="Entreprise A",
        location="Paris",
        city="Paris",
        postal_code="75001",
        distance_km=2.5,
        contract="CDI",
        salary_min=40000,
        salary_max=50000,
        salary_period="year",
        remote=True,
        remote_days=2,
        remote_type="hybrid",
        nearest_metro="Châtelet",
        metro_distance_km=0.5,
        date="31/08/2026",
        url="https://example.com/job-1",
        description="Description de l'offre",
        missions="Développer des applications",
        requirements="Expérience Python",
        education="Bac+3",
        skills="Python, Django"
    )

    rRow = vJob.to_csv_row()

    assert rRow == [
        "Développeur Python",
        "Entreprise A",
        "Paris",
        "Paris",
        "75001",
        2.5,
        "CDI",
        40000,
        50000,
        "year",
        True,
        2,
        "hybrid",
        "Châtelet",
        0.5,
        "31/08/2026",
        "https://example.com/job-1",
        "Description de l'offre",
        "Développer des applications",
        "Expérience Python",
        "Bac+3",
        "Python, Django"
    ]