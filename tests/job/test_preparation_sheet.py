"""Tests de la fiche de préparation d'entretien"""

from datetime import datetime

import pandas as pd

from job.interview_journal import record_interview
from job.preparation_sheet import (
    build_preparation_sheet,
    describe_interview_date,
    render_sheet_html,
)
from job.profile import EMPTY_PROFILE, save_profile
from storage.database import initialize_database
from storage.job_applications import save_application
from storage.job_offers import save_offers

NOW = datetime(2026, 10, 24, 9, 0)

OFFER = {
    "source": "lever",
    "source_id": "1",
    "title": "Développeur Python",
    "company": "Acme",
    "location": "Lille",
    "description": "Missions : développer des API FastAPI. Profil recherché : Python.",
}


def build_database(pTmpPath):
    """Crée une base avec l'offre, une autre offre d'Acme et un entretien noté."""

    rDatabaseFile = pTmpPath / "scraper.db"
    initialize_database(rDatabaseFile)
    save_offers(
        rDatabaseFile,
        pd.DataFrame(
            [
                OFFER,
                {
                    "source": "lever",
                    "source_id": "2",
                    "title": "Dev",
                    "company": "ACME",
                },
            ]
        ),
        NOW,
    )
    record_interview(rDatabaseFile, "lever", "2", NOW, "Pourquoi Acme ?", "")
    save_application(
        rDatabaseFile,
        "lever",
        "1",
        "INTERVIEW",
        pInterviewAt=datetime(2026, 10, 27, 14, 30),
    )

    return rDatabaseFile


def test_sheet_without_profile_still_gives_the_offer(tmp_path):
    """Vérifie la fiche sans profil : en-tête, résumé, questions de l'entreprise."""

    vSheet = build_preparation_sheet(build_database(tmp_path), OFFER)
    vNames = [vName for vName, _ in vSheet["sections"]]

    assert vSheet["title"] == "Développeur Python"
    assert vSheet["header"][:2] == ["Acme · Lille", "Entretien le 27/10/2026 à 14:30"]
    assert "Missions" in vNames
    assert ("Préparation", ["Remplissez la page Profil pour compléter la fiche."]) in (
        vSheet["sections"]
    )
    assert vSheet["sections"][-1][0] == "Déjà posées par cette entreprise"


def test_sheet_with_profile_lists_examples_and_escapes_html(tmp_path):
    """Vérifie les exemples à citer et l'échappement du HTML de la fiche."""

    vDatabaseFile = build_database(tmp_path)
    save_profile(
        vDatabaseFile,
        {
            **EMPTY_PROFILE,
            "skills": ["Python"],
            "experiences": [
                {"title": "Développeur", "skills": ["Python"], "achievement": "Une API"}
            ],
        },
    )

    vSheet = build_preparation_sheet(vDatabaseFile, {**OFFER, "title": "<b>Dev</b>"})
    vSections = dict(vSheet["sections"])
    vHtml = render_sheet_html(vSheet)

    assert vSections["Exemples à citer"] == ["Python : Développeur : Une API"]
    assert "Questions à poser" in vSections
    assert "&lt;b&gt;Dev&lt;/b&gt;" in vHtml
    assert "<b>Dev</b>" not in vHtml


def test_describe_interview_date():
    """Vérifie la date d'entretien, avec ou sans heure."""

    assert describe_interview_date("2026-10-27T14:30") == "27/10/2026 à 14:30"
    assert describe_interview_date("2026-10-27") == "27/10/2026"
