"""Tests de l'analyse de qualité des données"""

from datetime import datetime

import pandas as pd
import pytest

from job.quality import (
    build_quality_export,
    describe_problems,
    find_problems,
    get_quality_report,
    get_rate_tone,
)
from storage.database import initialize_database
from storage.job_offers import save_offers


@pytest.fixture
def database_file(tmp_path):
    """Crée une base avec une offre complète et une offre à vérifier."""

    rDatabaseFile = tmp_path / "scraper.db"

    initialize_database(rDatabaseFile)
    save_offers(
        rDatabaseFile,
        pd.DataFrame(
            [
                {
                    "source": "remotive",
                    "source_id": "1",
                    "title": "Développeur",
                    "company": "Acme",
                    "location": "Lille",
                    "description": "Offre complète",
                },
                {
                    "source": "remotive",
                    "source_id": "2",
                    "title": "=Data | Remote | France",
                    "salary_label": "selon profil",
                },
            ]
        ),
        datetime(2026, 10, 11),
    )

    return rDatabaseFile


@pytest.mark.parametrize(
    "pRate, pTone", [(80, "success"), (79, "warning"), (39, "danger")]
)
def test_get_rate_tone(pRate, pTone):
    """Vérifie les seuils de couleur des taux."""

    assert get_rate_tone(pRate) == pTone


def test_get_quality_report(database_file):
    """Vérifie les taux par source et toutes sources confondues."""

    vReport = get_quality_report(database_file)
    vCompany = vReport["columns"].index("Entreprise")

    assert vReport["rows"][0]["source"] == "Remotive"
    assert vReport["rows"][0]["count"] == 2
    assert vReport["rows"][0]["rates"][vCompany] == {"rate": 50, "tone": "warning"}
    assert vReport["total"]["count"] == 2
    assert vReport["rejected"] == 0
    assert vReport["problems"]["total"] == 1
    assert describe_problems(vReport["problems"]) == (
        "1 offre(s) à vérifier : description absente 1, entreprise absente 1, "
        "lieu absent 1, salaire non interprété 1, titre en plusieurs segments 1"
    )
    assert describe_problems({"total": 0, "kinds": []}) == "Aucune offre à vérifier."


def test_find_problems():
    """Vérifie la détection des défauts, télétravail compris pour le lieu."""

    assert find_problems({"title": "A | B", "salary_label": "45k", "remote": True}) == [
        "titre en plusieurs segments",
        "entreprise absente",
        "salaire non interprété",
        "description absente",
    ]
    assert find_problems({"title": "", "company": "Acme", "description": "x"}) == [
        "titre absent",
        "lieu absent",
    ]


def test_build_quality_export_lists_problems_safely(database_file):
    """Vérifie l'export des seules offres à vérifier, formules neutralisées."""

    vLines = build_quality_export(database_file).lstrip("﻿").splitlines()

    assert vLines[0].startswith("source;source_id;problems")
    assert len(vLines) == 2
    assert ";'=Data | Remote | France;" in vLines[1]
