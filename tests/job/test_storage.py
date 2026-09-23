# ============================================================================
# Tests du stockage des offres d'emploi
# ============================================================================

import csv

import pandas as pd
import pytest

from job.csv_schema import JOB_COLUMNS
from job.storage import save_jobs


def test_save_jobs(tmp_path):
    """
    Vérifie l'enregistrement des offres dans un fichier CSV.
    """

    vFilePath = tmp_path / "jobs.csv"

    vJobs = pd.DataFrame(
        [
            {
                "title": "Développeur Python",
                "company": "Entreprise A",
                "company_id": None,
                "source": "test",
                "source_id": "job-1",
                "location": "Paris",
                "city": "Paris",
                "postal_code": "75001",
                "country": "France",
                "distance_km": None,
                "contract": "CDI",
                "contract_type": "permanent",
                "employment_type": "full_time",
                "salary_min": None,
                "salary_max": None,
                "salary_currency": None,
                "salary_period": None,
                "remote": None,
                "remote_days": None,
                "remote_type": None,
                "nearest_metro": None,
                "metro_distance_km": None,
                "date": "31/08/2026",
                "published_at": None,
                "updated_at": None,
                "scraped_at": None,
                "url": "https://example.com/job-1",
                "description": "",
                "missions": "",
                "requirements": "",
                "education": "",
                "skills": "",
                "department": None,
                "experience_level": "junior",
                "job_type": "development"
            },
            {
                "title": "Développeur Java",
                "company": "Entreprise B",
                "company_id": None,
                "source": "test",
                "source_id": "job-2",
                "location": "Lille",
                "city": "Lille",
                "postal_code": "59000",
                "country": "France",
                "distance_km": None,
                "contract": "CDD",
                "contract_type": "temporary",
                "employment_type": "full_time",
                "salary_min": None,
                "salary_max": None,
                "salary_currency": None,
                "salary_period": None,
                "remote": None,
                "remote_days": None,
                "remote_type": None,
                "nearest_metro": None,
                "metro_distance_km": None,
                "date": "30/08/2026",
                "published_at": None,
                "updated_at": None,
                "scraped_at": None,
                "url": "https://example.com/job-2",
                "description": "",
                "missions": "",
                "requirements": "",
                "education": "",
                "skills": "",
                "department": None,
                "experience_level": "junior",
                "job_type": "development"
            }
        ]
    )

    save_jobs(
        vJobs,
        vFilePath
    )

    assert vFilePath.exists()

    with vFilePath.open(
        mode="r",
        encoding="utf-8",
        newline=""
    ) as vFile:
        vRows = list(
            csv.reader(vFile)
        )

    # Vérifie que l'ordre des colonnes du CSV respecte le schéma commun.
    assert vRows[0] == JOB_COLUMNS

    # Vérifie les principales valeurs de la première offre.
    assert vRows[1][JOB_COLUMNS.index("title")] == "Développeur Python"
    assert vRows[1][JOB_COLUMNS.index("company")] == "Entreprise A"
    assert vRows[1][JOB_COLUMNS.index("source")] == "test"
    assert vRows[1][JOB_COLUMNS.index("source_id")] == "job-1"
    assert vRows[1][JOB_COLUMNS.index("location")] == "Paris"
    assert vRows[1][JOB_COLUMNS.index("contract")] == "CDI"
    assert vRows[1][JOB_COLUMNS.index("url")] == (
        "https://example.com/job-1"
    )

    # Vérifie les principales valeurs de la seconde offre.
    assert vRows[2][JOB_COLUMNS.index("title")] == "Développeur Java"
    assert vRows[2][JOB_COLUMNS.index("company")] == "Entreprise B"
    assert vRows[2][JOB_COLUMNS.index("source")] == "test"
    assert vRows[2][JOB_COLUMNS.index("source_id")] == "job-2"
    assert vRows[2][JOB_COLUMNS.index("location")] == "Lille"
    assert vRows[2][JOB_COLUMNS.index("contract")] == "CDD"
    assert vRows[2][JOB_COLUMNS.index("url")] == (
        "https://example.com/job-2"
    )


def test_save_empty_jobs(tmp_path):
    """
    Vérifie l'enregistrement d'un DataFrame d'offres vide.
    """

    vFilePath = tmp_path / "jobs.csv"

    vJobs = pd.DataFrame(
        columns=JOB_COLUMNS
    )

    save_jobs(
        vJobs,
        vFilePath
    )

    assert vFilePath.exists()

    with vFilePath.open(
        mode="r",
        encoding="utf-8",
        newline=""
    ) as vFile:
        vRows = list(
            csv.reader(vFile)
        )

    assert vRows == [
        JOB_COLUMNS
    ]


def test_save_jobs_logs_error_when_file_cannot_be_written(
    tmp_path,
    monkeypatch
):
    """
    Vérifie qu'une erreur d'écriture est enregistrée dans les logs.
    """

    vFilePath = tmp_path / "jobs.csv"

    def mock_to_csv(*args, **kwargs):
        raise PermissionError(
            "Accès refusé"
        )

    monkeypatch.setattr(
        pd.DataFrame,
        "to_csv",
        mock_to_csv
    )

    vJobs = pd.DataFrame(
        [
            {
                "title": "Développeur Python",
                "company": "Entreprise A",
                "company_id": None,
                "source": "test",
                "source_id": "job-1",
                "location": "Paris",
                "city": "Paris",
                "postal_code": "75001",
                "country": "France",
                "distance_km": None,
                "contract": "CDI",
                "contract_type": "permanent",
                "employment_type": "full_time",
                "salary_min": None,
                "salary_max": None,
                "salary_currency": None,
                "salary_period": None,
                "remote": None,
                "remote_days": None,
                "remote_type": None,
                "nearest_metro": None,
                "metro_distance_km": None,
                "date": "31/08/2026",
                "published_at": None,
                "updated_at": None,
                "scraped_at": None,
                "url": "https://example.com/job-1",
                "description": "",
                "missions": "",
                "requirements": "",
                "education": "",
                "skills": "",
                "department": None,
                "experience_level": "junior",
                "job_type": "development"
            }
        ]
    )

    with pytest.raises(PermissionError):
        save_jobs(
            vJobs,
            vFilePath
        )