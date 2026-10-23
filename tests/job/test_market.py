"""Tests de la synthèse du marché"""

from datetime import datetime, timedelta

import pandas as pd

from job.market import build_market, build_market_cells
from job.profile import load_profile, save_profile
from storage.database import initialize_database
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
    assert build_market(vDatabaseFile, NOW + timedelta(days=200))["offer_count"] == 0
