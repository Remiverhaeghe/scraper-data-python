"""Tests du tableau de suivi et des statistiques de candidature"""

from datetime import datetime

import pandas as pd
import pytest

from job.application_tracking import (
    build_application_statistics,
    build_board,
    get_job_family,
)
from storage.database import initialize_database
from storage.job_applications import (
    get_application,
    save_application,
    update_application_status,
)
from storage.job_offers import save_offers

NOW = datetime(2026, 10, 11, 10, 0)

OFFERS = [
    ("1", "remotive", "Développeur Java", "Acme", "APPLIED"),
    ("2", "remotive", "Data engineer", "Acme", "INTERVIEW"),
    ("3", "adzuna", "Ingénieur DevOps", "Globex", "REJECTED"),
    ("4", "adzuna", "Chef de projet", "Globex", "INTERESTED"),
    ("5", "adzuna", "Vendeur", "Initech", "IGNORED"),
]


@pytest.fixture
def database_file(tmp_path):
    """Crée une base avec une candidature par statut."""

    rDatabaseFile = tmp_path / "scraper.db"

    initialize_database(rDatabaseFile)
    save_offers(
        rDatabaseFile,
        pd.DataFrame(
            [
                {
                    "source": vSource,
                    "source_id": vId,
                    "title": vTitle,
                    "company": vCompany,
                }
                for vId, vSource, vTitle, vCompany, _ in OFFERS
            ]
        ),
        NOW,
    )

    for vId, vSource, _, _, vStatus in OFFERS:
        save_application(rDatabaseFile, vSource, vId, vStatus, pNow=NOW)

    return rDatabaseFile


@pytest.mark.parametrize(
    "pTitle, pFamily",
    [
        ("Data Engineer H/F", "Data et IA"),
        ("Développeur Full Stack", "Développement"),
        ("Ingénieur systèmes et réseaux", "DevOps et cloud"),
        ("Testeur QA", "Test et qualité"),
        ("Chef de projet digital", "Projet et produit"),
        ("Vendeur", "Autre"),
        (None, "Autre"),
    ],
)
def test_get_job_family(pTitle, pFamily):
    """Vérifie le rangement des titres en familles de poste."""

    assert get_job_family(pTitle) == pFamily


def test_build_board_groups_cards(database_file):
    """Vérifie la répartition des cartes en colonnes, offres ignorées exclues."""

    vBoard = build_board(database_file, NOW)

    assert [vColumn["label"] for vColumn in vBoard] == [
        "À postuler",
        "Postulé",
        "Entretien",
        "Réponse",
    ]
    assert [[vCard["title"] for vCard in vColumn["cards"]] for vColumn in vBoard] == [
        ["Chef de projet"],
        ["Développeur Java"],
        ["Data engineer"],
        ["Ingénieur DevOps"],
    ]
    assert vBoard[1]["cards"][0]["applied_label"] == "11/10/2026"


def test_moving_to_applied_sets_dates(database_file):
    """Vérifie qu'un passage au statut Postulé fixe la date de candidature et la relance."""

    update_application_status(database_file, "adzuna", "4", "APPLIED", pNow=NOW)

    vApplication = get_application(database_file, "adzuna", "4")

    assert vApplication["applied_at"] == NOW.isoformat()
    assert vApplication["follow_up_date"].startswith("2026-10-18")


def test_build_application_statistics(database_file):
    """Vérifie les taux de réponse global et par dimension."""

    vStatistics = build_application_statistics(database_file)

    assert (vStatistics["sent"], vStatistics["answered"], vStatistics["rate"]) == (
        3,
        2,
        67,
    )
    assert vStatistics["interviews"] == 1

    vTables = dict(vStatistics["tables"])

    assert vTables["Par source"] == [
        {"label": "Remotive", "sent": 2, "answered": 1, "rate": 50},
        {"label": "Adzuna", "sent": 1, "answered": 1, "rate": 100},
    ]
    assert [vRow["label"] for vRow in vTables["Par type de poste"]] == [
        "Data et IA",
        "DevOps et cloud",
        "Développement",
    ]
    assert vTables["Par société"][0] == {
        "label": "Acme",
        "sent": 2,
        "answered": 1,
        "rate": 50,
    }


def test_statistics_without_application(tmp_path):
    """Vérifie l'absence de taux tant qu'aucune candidature n'est envoyée."""

    initialize_database(tmp_path / "scraper.db")

    assert build_application_statistics(tmp_path / "scraper.db")["rate"] is None
