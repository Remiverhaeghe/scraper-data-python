"""Tests du tableau de suivi et des statistiques de candidature"""

from datetime import datetime, timedelta

import pandas as pd
import pytest

from job.application_tracking import (
    build_application_statistics,
    build_board,
    build_follow_up_draft,
    build_funnel,
    get_job_family,
    get_week_follow_ups,
    mark_followed_up,
)
from job.profile import build_profile, save_profile
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
        {"label": "Remotive", "sent": 2, "answered": 1, "rate": 50, "delay": "—"},
        {"label": "Adzuna", "sent": 1, "answered": 1, "rate": 100, "delay": "—"},
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
        "delay": "—",
    }


def test_statistics_without_application(tmp_path):
    """Vérifie l'absence de taux tant qu'aucune candidature n'est envoyée."""

    initialize_database(tmp_path / "scraper.db")

    assert build_application_statistics(tmp_path / "scraper.db")["rate"] is None


def test_statistics_measure_first_response_delay(database_file):
    """Vérifie le délai jusqu'à la première réponse et le tableau par correspondance."""

    save_offers(
        database_file,
        pd.DataFrame(
            [
                {
                    "source": "remotive",
                    "source_id": "d",
                    "title": "Développeur Python Django SQL",
                }
            ]
        ),
        NOW,
    )
    save_application(database_file, "remotive", "d", "APPLIED", pNow=NOW)
    update_application_status(
        database_file, "remotive", "d", "INTERVIEW", pNow=NOW + timedelta(days=5)
    )
    save_application(
        database_file, "remotive", "d", "REJECTED", pNow=NOW + timedelta(days=9)
    )
    save_profile(database_file, build_profile("", "", "Python, Django, SQL", "", ""))

    vStatistics = build_application_statistics(database_file)
    vTables = dict(vStatistics["tables"])

    assert vStatistics["delay"] == "5 j"
    assert vTables["Par source"][0]["delay"] == "5 j"
    assert "Forte, 70 % et plus" in [
        vRow["label"] for vRow in vTables["Par correspondance au profil"]
    ]
    assert "Par contrat" in vTables


def test_week_follow_ups_and_drafts(database_file):
    """Vérifie la fenêtre de sept jours, le brouillon et la relance notée."""

    save_offers(
        database_file,
        pd.DataFrame(
            [
                {"source": "remotive", "source_id": "r1", "title": "Dev Go"},
                {"source": "remotive", "source_id": "r2", "title": "Dev Rust"},
            ]
        ),
        NOW,
    )
    save_application(
        database_file,
        "remotive",
        "r1",
        "APPLIED",
        pFollowUpDate=NOW - timedelta(days=1),
        pNow=NOW - timedelta(days=8),
    )
    save_application(
        database_file,
        "remotive",
        "r2",
        "APPLIED",
        pFollowUpDate=NOW + timedelta(days=10),
        pNow=NOW,
    )
    save_profile(database_file, build_profile("Camille D.", "", "", "", ""))

    vFollowUps = get_week_follow_ups(database_file, NOW)
    vTitles = [vFollowUp["title"] for vFollowUp in vFollowUps]

    assert "Dev Go" in vTitles
    assert "Dev Rust" not in vTitles

    vGo = vFollowUps[vTitles.index("Dev Go")]

    assert vGo["follow_up_due"]
    assert "poste de Dev Go, envoyée le 03/10/2026." in vGo["draft"]
    assert vGo["draft"].endswith("Bien cordialement,\nCamille D.")

    mark_followed_up(database_file, "remotive", "r1", NOW)

    vGo = next(
        vFollowUp
        for vFollowUp in get_week_follow_ups(database_file, NOW)
        if vFollowUp["title"] == "Dev Go"
    )

    assert not vGo["follow_up_due"]
    assert vGo["follow_up_count"] == 1


def test_follow_up_draft_without_company_or_name():
    """Vérifie un brouillon minimal, sans entreprise, date ni nom."""

    assert build_follow_up_draft({"title": None}, "") == (
        "Objet : ma candidature au poste de proposé\n\n"
        "Bonjour,\n\n"
        "Je me permets de revenir vers vous au sujet de ma candidature au poste "
        "de proposé.\n\n"
        "Ce poste m'intéresse toujours et je reste disponible pour un échange "
        "à votre convenance.\n\n"
        "Bien cordialement,"
    )


def test_funnel_shares_and_conversions():
    """Vérifie la part des envois et le passage d'une étape à l'autre."""

    vFunnel = build_funnel({"sent": 10, "answered": 4, "interviews": 2, "accepted": 0})

    assert [(vStage["count"], vStage["share"]) for vStage in vFunnel] == [
        (10, 100),
        (4, 40),
        (2, 20),
        (0, 0),
    ]
    assert [vStage["conversion"] for vStage in vFunnel] == [None, 40, 50, 0]
    assert build_funnel({"sent": 0, "answered": 0, "interviews": 0, "accepted": 0})[
        1
    ] == {"label": "Réponses", "count": 0, "share": 0, "conversion": None}


@pytest.mark.parametrize(
    "pApplication, pExpected",
    [
        (
            {
                "title": "Dev",
                "status": "INTERVIEW",
                "interview_at": "2026-10-14T10:00",
            },
            "notre entretien du 14/10/2026 au sujet du poste de Dev",
        ),
        (
            {
                "title": "Dev",
                "status": "APPLIED",
                "follow_up_count": 1,
                "last_follow_up_at": "2026-10-05T09:00:00",
            },
            "une dernière fois au sujet de ma candidature au poste de Dev, restée "
            "sans réponse depuis ma relance du 05/10/2026.",
        ),
    ],
)
def test_follow_up_draft_depends_on_stage(pApplication, pExpected):
    """Vérifie le brouillon après un entretien et à la deuxième relance."""

    assert pExpected in build_follow_up_draft(pApplication, "Camille")
