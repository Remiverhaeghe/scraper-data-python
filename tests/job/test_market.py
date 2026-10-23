"""Tests de la synthèse du marché"""

from datetime import datetime, timedelta

import pandas as pd

from job.market import (
    build_history_cells,
    build_market,
    build_market_cells,
    build_market_history,
    find_priority_skills,
)
from job.profile import load_profile, save_profile
from storage.database import initialize_database
from storage.geo_cache import save_offer_positions
from storage.job_offers import save_offers

NOW = datetime(2026, 10, 23, 12, 0)


def build_offer(pSourceId, pTitle, pSalary=None, pCity="Lille", **pValues):
    """Construit une offre en France, avec un salaire net mensuel facultatif."""

    rOffer = {
        "source": "adzuna",
        "source_id": pSourceId,
        "title": pTitle,
        "country": "France",
        "city": pCity,
        "contract": "CDI",
        "description": "Java et SQL",
        "salary_net_monthly_min": pSalary,
        "salary_net_monthly_max": pSalary,
    }

    rOffer.update(pValues)

    return rOffer


def test_market_counts_skills_and_cities_with_median(tmp_path):
    """Vérifie volumes, médianes à partir de trois salaires et offres écartées."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    save_profile(vDatabaseFile, {**load_profile(vDatabaseFile), "skills": ["Java"]})
    save_offers(
        vDatabaseFile,
        pd.DataFrame(
            [
                build_offer("1", "Développeur Java", 2800),
                build_offer("2", "Développeur Java", 3000),
                build_offer("3", "Développeur Java", 3200, pCity="Paris"),
                build_offer("4", "Développeur Java", None, pCity=None),
                build_offer("5", "Stage développeur Java", 1000),
                build_offer("6", "Développeur Java", 9000, contract="FREELANCE"),
            ]
        ),
        NOW - timedelta(days=2),
    )

    vMarket = build_market(vDatabaseFile, NOW)

    assert vMarket["offer_count"] == 4
    assert vMarket["salaried_count"] == 3
    assert vMarket["median"] == "3 000 €"
    assert vMarket["target"] is None
    assert vMarket["unknown_city_count"] == 1
    assert build_market_cells(vMarket["skills"][0], True) == [
        "Java",
        "4",
        "100 %",
        "3",
        "3 000 €",
        "oui",
    ]
    assert [vRow["name"] for vRow in vMarket["cities"]] == ["Lille", "Paris"]
    assert vMarket["cities"][1]["median"] == "—"
    assert vMarket["regions"] == []
    assert vMarket["unknown_region_count"] == 4
    assert build_market(vDatabaseFile, NOW + timedelta(days=200))["offer_count"] == 0


def test_market_groups_placed_offers_by_region(tmp_path):
    """Vérifie le regroupement par région des offres placées sur la carte."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    save_offers(
        vDatabaseFile,
        pd.DataFrame(
            [
                build_offer("1", "Développeur Java", pCity="Roubaix"),
                build_offer("2", "Développeur Java", pCity="Lille"),
                build_offer("3", "Développeur Java", pCity="Lyon"),
            ]
        ),
        NOW - timedelta(days=2),
    )
    save_offer_positions(
        vDatabaseFile,
        [
            (50.69, 3.17, "59", "adzuna", "1"),
            (50.63, 3.06, "59", "adzuna", "2"),
            (45.75, 4.83, "69", "adzuna", "3"),
        ],
    )

    vRegions = build_market(vDatabaseFile, NOW)["regions"]

    assert [(vRow["name"], vRow["count"]) for vRow in vRegions] == [
        ("Hauts-de-France", 2),
        ("Auvergne-Rhône-Alpes", 1),
    ]


def test_priorities_are_demanded_skills_little_mastered():
    """Vérifie les priorités : les plus demandées, non évaluées ou notées sous 5."""

    vPriorities = find_priority_skills(
        {"Java": [None] * 5, "SQL": [None] * 4, "Docker": [None] * 3, "Git": [None]},
        {"Java": 7, "SQL": 2},
    )

    assert [(vSkill["name"], vSkill["label"]) for vSkill in vPriorities] == [
        ("SQL", "4 offre(s) · niveau 2/10"),
        ("Docker", "3 offre(s) · non évaluée"),
        ("Git", "1 offre(s) · non évaluée"),
    ]


def test_history_counts_offers_per_month(tmp_path):
    """Vérifie l'évolution par mois, mois vides du début retirés."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    save_profile(vDatabaseFile, {**load_profile(vDatabaseFile), "skills": ["Java"]})
    save_offers(
        vDatabaseFile,
        pd.DataFrame([build_offer("1", "Développeur Java", 3000)]),
        datetime(2026, 9, 1, 8, 0),
    )
    save_offers(
        vDatabaseFile,
        pd.DataFrame(
            [
                build_offer("2", "Développeur PHP", description="PHP"),
                build_offer("3", "Développeur Java", 3200),
            ]
        ),
        NOW - timedelta(days=2),
    )

    vHistory = build_market_history(vDatabaseFile, NOW)

    assert [
        (vMonth["label"], vMonth["offers"], vMonth["mine"]) for vMonth in vHistory
    ] == [
        ("sept. 2026", 1, 1),
        ("oct. 2026", 2, 1),
    ]
    assert build_history_cells(vHistory[1]) == ["oct. 2026", "2", "1", "—"]
