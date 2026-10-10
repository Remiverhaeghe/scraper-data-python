"""Tests de la transformation des offres France Travail"""

import pytest

from job.csv_schema import JOB_COLUMNS
from job.sources.france_travail.parser import parse_job, parse_jobs, parse_salary


def test_parse_job():
    """Vérifie la transformation d'une offre France Travail."""

    vJob = {
        "id": "123",
        "intitule": "Développeur Python",
        "description": "Développement Python",
        "typeContrat": "CDI",
        "typeContratLibelle": "CDI",
        "experienceLibelle": "Débutant accepté",
        "dateCreation": "2026-09-22",
        "dateActualisation": "2026-09-22",
        "entreprise": {"nom": "Entreprise A"},
        "lieuTravail": {"libelle": "Paris", "commune": "Paris", "codePostal": "75001"},
        "salaire": {"libelle": "Annuel de 35000.0 Euros à 45000.0 Euros sur 12 mois"},
        "origineOffre": {"urlOrigine": "https://example.com/job/123"},
        "formations": "Bac +2",
        "competences": [{"libelle": "Python"}],
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
    assert rJob["salary_period"] == "year"


def test_parse_job_with_missing_values():
    """Vérifie qu'une offre partiellement renseignée est acceptée."""

    rJob = parse_job({"id": "456", "intitule": "Développeur Java"})

    assert rJob["title"] == "Développeur Java"
    assert rJob["source"] == "france_travail"
    assert rJob["source_id"] == "456"
    assert rJob["company"] is None
    assert rJob["salary_min"] is None


def test_parse_jobs():
    """Vérifie la transformation de plusieurs offres."""

    vJobs = [
        {"id": "1", "intitule": "Développeur Python"},
        {"id": "2", "intitule": "Développeur Java"},
    ]

    rDataFrame = parse_jobs(vJobs)

    assert len(rDataFrame) == 2
    assert list(rDataFrame.columns) == JOB_COLUMNS
    assert rDataFrame.iloc[0]["title"] == "Développeur Python"
    assert rDataFrame.iloc[1]["title"] == "Développeur Java"


def test_parse_empty_jobs():
    """Vérifie la transformation d'une liste vide."""

    rDataFrame = parse_jobs([])

    assert rDataFrame.empty
    assert list(rDataFrame.columns) == JOB_COLUMNS


@pytest.mark.parametrize(
    "pLabel, pExpected",
    [
        ("Mensuel de 2000.00 Euros à 2500.00 Euros sur 12 mois", (2000, 2500, "month")),
        ("Annuel de 40000.0 Euros sur 12.0 mois", (40000, None, "year")),
        ("Horaire de 11.88 Euros sur 12 mois", (11.88, None, "hour")),
        ("Selon profil", (None, None, None)),
        (None, (None, None, None)),
    ],
)
def test_parse_salary(pLabel, pExpected):
    """Vérifie l'extraction du salaire depuis le libellé France Travail."""

    assert parse_salary(pLabel) == pExpected


def test_parse_job_builds_url_when_missing():
    """Vérifie que l'URL de l'offre est reconstruite si la source ne la fournit pas."""

    rJob = parse_job({"id": "123ABC"})

    assert rJob["url"] == (
        "https://candidat.francetravail.fr/offres/recherche/detail/123ABC"
    )


def test_parse_job_keeps_salary_label_with_complements():
    """Vérifie la conservation du libellé de salaire et de ses compléments."""

    rJob = parse_job(
        {
            "id": "1",
            "salaire": {
                "libelle": "Mensuel de 2500.00 Euros sur 13 mois",
                "complement1": "Primes",
                "listeComplements": [{"code": "1", "libelle": "Intéressement"}],
            },
        }
    )

    assert rJob["salary_label"] == (
        "Mensuel de 2500.00 Euros sur 13 mois | Primes | Intéressement"
    )


@pytest.mark.parametrize(
    "pCode, pExpected",
    [("CDI", "CDI"), ("SAI", "CDD"), ("LIB", "FREELANCE"), ("MIS", None)],
)
def test_parse_job_normalizes_contract(pCode, pExpected):
    """Vérifie la conversion des codes de contrat France Travail."""

    rJob = parse_job({"id": "1", "typeContrat": pCode})

    assert rJob["contract"] == pExpected
    assert rJob["contract_type"] == pCode
