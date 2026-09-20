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


def test_job_from_csv_row():
    """
    Vérifie la création d'une offre depuis une ligne CSV.
    """

    vRow = {
        "title": "Développeur Python",
        "company": "Entreprise A",
        "location": "Paris",
        "contract": "CDI",
        "date": "31/08/2026",
        "url": "https://example.com/job-1"
    }

    rJob = Job.from_csv_row(vRow)

    assert isinstance(rJob, Job)
    assert rJob.title == "Développeur Python"
    assert rJob.company == "Entreprise A"
    assert rJob.location == "Paris"
    assert rJob.contract == "CDI"
    assert rJob.date == "31/08/2026"
    assert rJob.url == "https://example.com/job-1"


def test_job_to_csv_row():
    """
    Vérifie la conversion d'une offre vers une ligne CSV.
    """

    vJob = Job(
        title="Développeur Python",
        company="Entreprise A",
        location="Paris",
        contract="CDI",
        date="31/08/2026",
        url="https://example.com/job-1"
    )

    rRow = vJob.to_csv_row()

    assert rRow == [
        "Développeur Python",
        "Entreprise A",
        "Paris",
        "CDI",
        "31/08/2026",
        "https://example.com/job-1"
    ]