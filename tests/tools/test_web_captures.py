"""Tests de la base fictive des captures du tableau de bord"""

from datetime import datetime

from storage.job_applications import get_application
from storage.job_offers import count_offers, get_offers
from job.market import build_market
from tools.web_captures import (
    APPLICATIONS,
    DEMO_SOURCE,
    OFFERS,
    POSITIONS,
    fill_database,
)


def test_demo_database_holds_every_offer_and_application(tmp_path):
    """Vérifie que chaque offre fictive est enregistrée avec son suivi."""

    vDatabaseFile = tmp_path / "scraper.db"

    fill_database(vDatabaseFile, datetime(2026, 11, 17, 9, 0))

    assert count_offers(vDatabaseFile) == len(OFFERS)
    assert set(get_offers(vDatabaseFile)["company"]) == {vOffer[1] for vOffer in OFFERS}

    for vIndex, vStatus, _ in APPLICATIONS:
        assert (
            get_application(vDatabaseFile, DEMO_SOURCE, str(vIndex))["status"]
            == vStatus
        )


def test_every_demo_city_has_a_position():
    """Vérifie qu'aucune offre fictive ne manque sur la carte."""

    assert {vOffer[2] for vOffer in OFFERS} <= set(POSITIONS)


def test_market_page_shows_demo_salaries(tmp_path):
    """Vérifie que la page du marché tient compte des salaires fictifs."""

    vDatabaseFile = tmp_path / "scraper.db"
    vNow = datetime(2026, 11, 17, 9, 0)

    fill_database(vDatabaseFile, vNow)

    assert build_market(vDatabaseFile, vNow)["salaried_count"] == sum(
        1 for vOffer in OFFERS if vOffer[5]
    )
