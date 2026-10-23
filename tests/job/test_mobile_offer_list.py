"""Tests de la liste d'offres envoyée au téléphone"""

from datetime import datetime, timedelta

import pandas as pd

from job.geocoding import HOME_KEY
from job.mobile_sync import build_offer_list
from storage.database import initialize_database
from storage.job_applications import save_application
from storage.geo_cache import save_offer_positions
from storage.job_offers import save_offers
from storage.settings_repository import save_json_setting

NOW = datetime(2026, 10, 23, 12)


def test_offer_list_flags_and_adds_offers_close_to_retained_ones(tmp_path):
    """Vérifie l'offre proche d'une offre retenue, signalée par similar_to."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    save_offers(
        vDatabaseFile,
        pd.DataFrame(
            [
                {
                    "source": "lever",
                    "source_id": "ref",
                    "title": "Technicien de maintenance",
                    "skills": ["GMAO", "Pneumatique"],
                }
            ]
        ),
        NOW - timedelta(days=30),
    )
    save_offers(
        vDatabaseFile,
        pd.DataFrame(
            [
                {
                    "source": "lever",
                    "source_id": "proche",
                    "title": "Technicien maintenance industrielle",
                    "skills": ["GMAO"],
                }
            ]
        ),
        NOW - timedelta(days=1),
    )
    save_application(vDatabaseFile, "lever", "ref", "APPLIED", pNow=NOW)

    vOffers = {
        vOffer["source_id"]: vOffer for vOffer in build_offer_list(vDatabaseFile, NOW)
    }

    assert vOffers["proche"]["similar_to"] == "Technicien de maintenance"
    assert vOffers["proche"]["covered"] == []
    assert vOffers["proche"]["missing"] == ["GMAO"]
    assert {"description", "salary"} <= set(vOffers["proche"])


def test_offer_list_gives_position_and_near_flag(tmp_path):
    """Vérifie la position envoyée et l'offre signalée dans le rayon des alertes."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    save_offers(
        vDatabaseFile,
        pd.DataFrame(
            [
                {
                    "source": "lever",
                    "source_id": "lille",
                    "title": "Dev",
                    "country": "France",
                },
                {
                    "source": "lever",
                    "source_id": "remote",
                    "title": "Dev",
                    "remote": True,
                },
            ]
        ),
        NOW - timedelta(days=1),
    )
    save_offer_positions(vDatabaseFile, [(50.63, 3.06, "59", "lever", "lille")])
    save_json_setting(
        vDatabaseFile,
        HOME_KEY,
        {
            "label": "Roubaix",
            "latitude": 50.69,
            "longitude": 3.18,
            "alert_radius_km": 30,
        },
    )

    vOffers = {
        vOffer["source_id"]: vOffer for vOffer in build_offer_list(vDatabaseFile, NOW)
    }

    assert vOffers["lille"]["latitude"] == 50.63
    assert vOffers["lille"]["near"] is True
    assert vOffers["remote"]["near"] is False
