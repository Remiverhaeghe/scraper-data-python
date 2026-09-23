# ============================================================================
# Tests de la transformation des offres France Travail
# ============================================================================

from job.csv_schema import JOB_COLUMNS
from job.sources.france_travail.parser import (
    parse_job,
    parse_jobs
)


def test_parse_job():
    """
    Vérifie la transformation d'une offre France Travail.
    """

    vJob = {
        "id": "123",
        "intitule": "Développeur Python",
        "description": "Développement Python",
        "typeContrat": "CDI",
        "typeContratLibelle": "CDI",
        "experienceLibelle": "Débutant accepté",
        "dateCreation": "2026-09-22",
        "dateActualisation": "2026-09-22",
        "entreprise": {
            "nom": "Entreprise A"
        },
        "lieuTravail": {
            "libelle": "Paris",
            "commune": "Paris",
            "codePostal": "75001"
        },
        "salaire": {
            "min": 35000,
            "max": 45000,
            "libelle": "Annuel"
        },
        "origineOffre": {
            "urlOrigine": "https://example.com/job/123"
        },
        "formations": "Bac +2",
        "competences": [
            {
                "libelle": "Python"
            }
        ]
    }

    rJob = parse_job(vJob)

    assert rJob["title"] == "Développeur Python"
    assert rJob["company"] == "Entreprise A"
    assert rJob["source"] == "france_travail"
    assert rJob["source_id"] == "123"
    assert rJob["city"] == "Paris"
    assert rJob["postal_code"] == "75001"
    assert rJob["contract"] == "CDI"
    assert rJob["salary_min"] == 35000
    assert rJob["salary_max"] == 45000
    assert rJob["salary_currency"] == "EUR"
    assert rJob["salary_period"] == "Annuel"


def test_parse_job_with_missing_values():
    """
    Vérifie qu'une offre partiellement renseignée est acceptée.
    """

    rJob = parse_job(
        {
            "id": "456",
            "intitule": "Développeur Java"
        }
    )

    assert rJob["title"] == "Développeur Java"
    assert rJob["source"] == "france_travail"
    assert rJob["source_id"] == "456"
    assert rJob["company"] is None
    assert rJob["salary_min"] is None


def test_parse_jobs():
    """
    Vérifie la transformation de plusieurs offres.
    """

    vJobs = [
        {
            "id": "1",
            "intitule": "Développeur Python"
        },
        {
            "id": "2",
            "intitule": "Développeur Java"
        }
    ]

    rDataFrame = parse_jobs(vJobs)

    assert len(rDataFrame) == 2
    assert list(rDataFrame.columns) == JOB_COLUMNS
    assert rDataFrame.iloc[0]["title"] == "Développeur Python"
    assert rDataFrame.iloc[1]["title"] == "Développeur Java"


def test_parse_empty_jobs():
    """
    Vérifie la transformation d'une liste vide.
    """

    rDataFrame = parse_jobs([])

    assert rDataFrame.empty
    assert list(rDataFrame.columns) == JOB_COLUMNS