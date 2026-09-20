# ============================================================================
# Tests du stockage des offres d'emploi
# ============================================================================


import csv
from pathlib import Path

import pytest

from job.model import Job
from job.storage import save_jobs


def test_save_jobs(tmp_path):
    """
    Vérifie l'enregistrement des offres dans un fichier CSV.
    """

    vFilePath = tmp_path / "jobs.csv"

    vJobs = [
        Job(
            title="Développeur Python",
            company="Entreprise A",
            location="Paris",
            contract="CDI",
            date="31/08/2026",
            url="https://example.com/job-1"
        ),
        Job(
            title="Développeur Java",
            company="Entreprise B",
            location="Lille",
            contract="CDD",
            date="30/08/2026",
            url="https://example.com/job-2"
        )
    ]

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
        "contract",
        "date",
        "url"
    ]

    assert vRows[1] == [
        "Développeur Python",
        "Entreprise A",
        "Paris",
        "CDI",
        "31/08/2026",
        "https://example.com/job-1"
    ]

    assert vRows[2] == [
        "Développeur Java",
        "Entreprise B",
        "Lille",
        "CDD",
        "30/08/2026",
        "https://example.com/job-2"
    ]


def test_save_empty_jobs(tmp_path):
    """
    Vérifie l'enregistrement d'une liste d'offres vide.
    """

    vFilePath = tmp_path / "jobs.csv"

    save_jobs(
        [],
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

    assert vRows == [[
        "title",
        "company",
        "location",
        "contract",
        "date",
        "url"
    ]]


def test_save_jobs_logs_error_when_file_cannot_be_written(
    tmp_path,
    monkeypatch
):
    """
    Vérifie qu'une erreur d'écriture est enregistrée dans les logs.
    """

    vFilePath = tmp_path / "jobs.csv"

    def mock_open(*args, **kwargs):
        raise PermissionError(
            "Accès refusé"
        )

    monkeypatch.setattr(
        Path,
        "open",
        mock_open
    )

    vJobs = [
        Job(
            title="Développeur Python",
            company="Entreprise A",
            location="Paris",
            contract="CDI",
            date="31/08/2026",
            url="https://example.com/job-1"
        )
    ]

    with pytest.raises(PermissionError):
        save_jobs(
            vJobs,
            vFilePath
        )