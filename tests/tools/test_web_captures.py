"""Tests de la base fictive des captures du tableau de bord"""

from datetime import datetime

from storage.job_applications import get_application
from storage.job_offers import count_offers, get_offers
from tools.web_captures import APPLICATIONS, OFFERS, POSITIONS, fill_database


def test_demo_database_holds_every_offer_and_application(tmp_path):
    """Vérifie que chaque offre fictive est enregistrée avec son suivi."""

    vDatabaseFile = tmp_path / "scraper.db"

    fill_database(vDatabaseFile, datetime(2026, 11, 17, 9, 0))

    assert count_offers(vDatabaseFile) == len(OFFERS)
    assert set(get_offers(vDatabaseFile)["company"]) == {vOffer[1] for vOffer in OFFERS}

    for vIndex, vStatus, _ in APPLICATIONS:
        assert get_application(vDatabaseFile, "demo", str(vIndex))["status"] == vStatus


def test_every_demo_city_has_a_position():
    """Vérifie qu'aucune offre fictive ne manque sur la carte."""

    assert {vOffer[2] for vOffer in OFFERS} <= set(POSITIONS)
