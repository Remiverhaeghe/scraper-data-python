"""Tests du salaire du marché"""

from datetime import datetime

import pandas as pd

from job.salary_market import (
    add_estimated_salaries,
    describe_market_salary,
    describe_negotiation,
    find_market_salary,
    is_training,
    to_gross_yearly,
)
from job.settings import save_settings
from storage.database import initialize_database
from storage.job_offers import save_offers

NOW = datetime(2026, 10, 23, 12)


def build_offer(pId, pTitle, pSkills, pSalary, pContract="CDI"):
    """Construit une offre française avec ses compétences et son net mensuel."""

    rOffer = {
        "source": "lever",
        "source_id": pId,
        "title": pTitle,
        "skills": pSkills,
        "country": "France",
        "contract": pContract,
        "salary_net_monthly_min": pSalary,
        "salary_net_monthly_max": pSalary,
    }

    return rOffer


def test_market_salary_compares_close_offers_of_the_same_kind(tmp_path):
    """Vérifie la médiane des offres proches, sans stage, freelance ni intrus."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    vJava = ["Java", "SQL", "Spring"]
    save_offers(
        vDatabaseFile,
        pd.DataFrame(
            [
                build_offer("1", "Développeur", vJava, 2400),
                build_offer("2", "Développeur", vJava, 2600),
                build_offer("3", "Développeur", ["Java", "SQL"], 2800),
                build_offer("4", "Stage développeur", vJava, 900),
                build_offer("5", "Mission", vJava, 9000, "FREELANCE"),
                build_offer("6", "Comptable", ["Excel", "SAP"], 2000),
            ]
        ),
        NOW,
    )
    vOffer = {"source": "x", "source_id": "1", "title": "Lead Java", "skills": vJava}

    vMarket = find_market_salary(vDatabaseFile, vOffer)

    assert (vMarket["median"], vMarket["count"]) == (2600, 3)
    assert describe_market_salary(vMarket).startswith(
        "2 600 € net médian sur 3 offres proches"
    )
    assert find_market_salary(vDatabaseFile, {**vOffer, "title": "Stage Java"}) is None
    assert find_market_salary(vDatabaseFile, {"title": "Vendeur"}) is None

    save_settings(vDatabaseFile, {"target_net_salary": "3000"})
    vMarket = find_market_salary(vDatabaseFile, vOffer)

    assert describe_market_salary(vMarket).endswith("au-dessus du marché")

    for vTarget, vPosition in ((2600, "dans le marché"), (2000, "en dessous")):
        vText = describe_market_salary({**vMarket, "target": vTarget})

        assert vPosition in vText

    assert describe_market_salary(None).startswith("Pas encore assez")


def test_is_training():
    """Vérifie le repérage d'un stage ou d'une alternance par l'intitulé."""

    assert is_training({"title": "Software Engineer Intern"})
    assert is_training({"title": "Développeur en alternance"})
    assert not is_training({"title": "Développeur internationalisation"})


def test_negotiation_gives_gross_yearly_range_and_ask():
    """Vérifie l'argumentaire : brut annuel, demande au moins égale à la médiane."""

    vSettings = {"net_salary_percent": 75, "income_tax_rate": 0}
    vMarket = {"median": 3000, "low": 2500, "high": 3500, "count": 6, "target": 2800}

    vText = describe_negotiation(
        vMarket, {"salary_net_monthly_min": 3600}, vSettings
    ).replace(" ", " ")

    assert to_gross_yearly(3000, vSettings) == 48000
    assert vText.startswith("Offres proches : 40 000 € à 56 000 € brut annuel")
    assert "demande appuyée par le marché : 48 000 € brut annuel" in vText
    assert vText.endswith("l'offre annonce plus que le marché")
    assert describe_negotiation(None, {}, vSettings) == ""


def test_offers_without_salary_get_an_estimate(tmp_path):
    """Vérifie l'estimation : médiane des offres proches, seulement en France."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    save_offers(
        vDatabaseFile,
        pd.DataFrame(
            [
                build_offer(str(vId), "Développeur", ["Java", "SQL"], vSalary)
                for vId, vSalary in ((1, 2800), (2, 3000), (3, 3400))
            ]
        ),
        NOW,
    )
    vOffers = [
        build_offer("a", "Développeur Java", ["Java", "SQL"], None),
        {
            **build_offer("b", "Développeur Java", ["Java", "SQL"], None),
            "country": "Allemagne",
        },
        build_offer("c", "Développeur Java", ["Java", "SQL"], 3100),
    ]

    add_estimated_salaries(vDatabaseFile, vOffers)

    assert vOffers[0]["estimated_salary"] == "3 000 €"
    assert vOffers[1]["estimated_salary"] is None
    assert vOffers[2]["estimated_salary"] is None
