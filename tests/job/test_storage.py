# ============================================================================
# Tests du stockage des offres d'emploi
# ============================================================================

import csv

import pandas as pd
import pytest

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
                "location": "Paris",
                "city": "",
                "postal_code": "",
                "distance_km": None,
                "contract": "CDI",
                "salary_min": None,
                "salary_max": None,
                "salary_period": None,
                "remote": None,
                "remote_days": None,
                "remote_type": None,
                "nearest_metro": None,
                "metro_distance_km": None,
                "date": "31/08/2026",
                "url": "https://example.com/job-1",
                "description": "",
                "missions": "",
                "requirements": "",
                "education": "",
                "skills": ""
            },
            {
                "title": "Développeur Java",
                "company": "Entreprise B",
                "location": "Lille",
                "city": "",
                "postal_code": "",
                "distance_km": None,
                "contract": "CDD",
                "salary_min": None,
                "salary_max": None,
                "salary_period": None,
                "remote": None,
                "remote_days": None,
                "remote_type": None,
                "nearest_metro": None,
                "metro_distance_km": None,
                "date": "30/08/2026",
                "url": "https://example.com/job-2",
                "description": "",
                "missions": "",
                "requirements": "",
                "education": "",
                "skills": ""
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

    assert vRows[0] == [
        "title",
        "company",
        "location",
        "city",
        "postal_code",
        "distance_km",
        "contract",
        "salary_min",
        "salary_max",
        "salary_period",
        "remote",
        "remote_days",
        "remote_type",
        "nearest_metro",
        "metro_distance_km",
        "date",
        "url",
        "description",
        "missions",
        "requirements",
        "education",
        "skills"
    ]

    assert vRows[1] == [
        "Développeur Python",
        "Entreprise A",
        "Paris",
        "",
        "",
        "",
        "CDI",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "31/08/2026",
        "https://example.com/job-1",
        "",
        "",
        "",
        "",
        ""
    ]

    assert vRows[2] == [
        "Développeur Java",
        "Entreprise B",
        "Lille",
        "",
        "",
        "",
        "CDD",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "30/08/2026",
        "https://example.com/job-2",
        "",
        "",
        "",
        "",
        ""
    ]


def test_save_empty_jobs(tmp_path):
    """
    Vérifie l'enregistrement d'un DataFrame d'offres vide.
    """

    vFilePath = tmp_path / "jobs.csv"

    vJobs = pd.DataFrame(
        columns=[
            "title",
            "company",
            "location",
            "city",
            "postal_code",
            "distance_km",
            "contract",
            "salary_min",
            "salary_max",
            "salary_period",
            "remote",
            "remote_days",
            "remote_type",
            "nearest_metro",
            "metro_distance_km",
            "date",
            "url",
            "description",
            "missions",
            "requirements",
            "education",
            "skills"
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

    assert vRows == [
        [
            "title",
            "company",
            "location",
            "city",
            "postal_code",
            "distance_km",
            "contract",
            "salary_min",
            "salary_max",
            "salary_period",
            "remote",
            "remote_days",
            "remote_type",
            "nearest_metro",
            "metro_distance_km",
            "date",
            "url",
            "description",
            "missions",
            "requirements",
            "education",
            "skills"
        ]
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
                "location": "Paris",
                "city": "",
                "postal_code": "",
                "distance_km": None,
                "contract": "CDI",
                "salary_min": None,
                "salary_max": None,
                "salary_period": None,
                "remote": None,
                "remote_days": None,
                "remote_type": None,
                "nearest_metro": None,
                "metro_distance_km": None,
                "date": "31/08/2026",
                "url": "https://example.com/job-1",
                "description": "",
                "missions": "",
                "requirements": "",
                "education": "",
                "skills": ""
            }
        ]
    )

    with pytest.raises(PermissionError):
        save_jobs(
            vJobs,
            vFilePath
        )