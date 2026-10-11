"""Tests de l'enrichissement des offres à partir de leur description"""

import pandas as pd
import pytest

from job.enrichment import (
    detect_experience,
    detect_remote,
    detect_salary,
    detect_skills,
    enrich_offers,
)


@pytest.mark.parametrize(
    "pText, pExpected",
    [
        ("Poste en full remote", (True, "full", None)),
        ("Télétravail complet possible", (True, "full", None)),
        ("2 jours de télétravail par semaine", (True, "hybrid", 2)),
        ("Hybrid, 3 days remote", (True, "hybrid", 3)),
        ("Organisation hybride", (True, "hybrid", None)),
        ("Pas de télétravail sur ce poste", (False, None, None)),
        ("Bureaux à Lille", None),
    ],
)
def test_detect_remote(pText, pExpected):
    """Vérifie le télétravail complet, hybride avec ses jours, ou exclu."""

    assert detect_remote(pText) == pExpected


@pytest.mark.parametrize(
    "pText, pExpected",
    [
        ("3 ans d'expérience minimum", "3 ans"),
        ("5+ years of experience", "5 ans"),
        ("Poste ouvert aux débutants", "Débutant"),
        ("Profil senior attendu", "Senior"),
        ("Développeur confirmé", "Confirmé"),
        ("Aucune précision", None),
    ],
)
def test_detect_experience(pText, pExpected):
    """Vérifie l'expérience en années, sinon le niveau nommé."""

    assert detect_experience(pText) == pExpected


@pytest.mark.parametrize(
    "pText, pExpected",
    [
        ("Salaire 45 - 55 k€ brut", (45000.0, 55000.0, "EUR", "year")),
        ("€70k - €90k", (70000.0, 90000.0, "EUR", "year")),
        ("$120k-$150k", (120000.0, 150000.0, "USD", "year")),
        ("jusqu'à 60k€", (60000.0, None, "EUR", "year")),
        ("42 000 € - 48 000 € brut annuel", (42000.0, 48000.0, "EUR", "year")),
        ("2 800 € par mois", (2800.0, None, "EUR", "month")),
        ("35 000 €", (35000.0, None, "EUR", "year")),
        ("Prime de 1 000 € à l'embauche", None),
        ("Mission de 45k sans devise", None),
        ("€60kilos de matériel", None),
    ],
)
def test_detect_salary(pText, pExpected):
    """Vérifie les formats de salaire reconnus et les montants écartés."""

    assert detect_salary(pText) == pExpected


def test_detect_skills_avoids_ambiguous_matches():
    """Vérifie que Java n'est pas confondu avec JavaScript."""

    assert detect_skills("Stack : JavaScript, React, Docker") == [
        "JavaScript",
        "React",
        "Docker",
    ]
    assert detect_skills("Java et Spring Boot") == ["Java", "Spring"]


def test_enrich_offers_fills_only_empty_fields_and_rejects_unusable():
    """Vérifie que la source garde la priorité et que les offres vides sont écartées."""

    vItems = pd.DataFrame(
        [
            {
                "title": "Développeur Python",
                "description": "Full remote, 4 ans d'expérience, 50 - 60 k€, Django",
                "remote": None,
                "skills": None,
                "experience_level": "Junior",
                "salary_min": None,
                "salary_max": None,
            },
            {"title": None, "description": None},
        ]
    )

    rItems, rRejected = enrich_offers(vItems)
    vOffer = rItems.iloc[0]

    assert rRejected == 1
    assert len(rItems) == 1
    assert vOffer["remote"]
    assert vOffer["remote_type"] == "full"
    assert vOffer["skills"] == ["Python", "Django"]
    assert vOffer["experience_level"] == "Junior"
    assert (vOffer["salary_min"], vOffer["salary_max"]) == (50000.0, 60000.0)
    assert vOffer["salary_currency"] == "EUR"
