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