"""Tests de la position du domicile et des offres"""

from datetime import datetime

import pandas as pd
import pytest
import requests

import job.geocoding as geocoding
from job.geocoding import (
    is_locatable,
    load_home,
    locate_offers,
    save_home,
)
from storage.database import initialize_database
from storage.geo_cache import get_cached_locations
from storage.job_offers import get_offers, save_offers

# Positions renvoyées par le géocodeur simulé, avec leur libellé
PLACES = {
    "59000 Lille": (50.6366, 3.0635, "Lille"),
    "Roubaix": (50.6942, 3.1746, "Roubaix"),
    "Lyon": (45.758, 4.835, "Lyon"),
}

NOW = datetime(2026, 10, 23, 12)


@pytest.fixture(name="geocoder")
def fixture_geocoder(monkeypatch):
    """Remplace le géocodeur par les lieux de PLACES ; retourne les requêtes reçues."""

    rQueries = []

    def answer(_pMethod, _pUrl, pParams, **_pOptions):
        rQueries.append(pParams)
        vPlace = PLACES.get(pParams["q"])

        return {
            "features": (
                [
                    {
                        "geometry": {"coordinates": [vPlace[1], vPlace[0]]},
                        "properties": {"label": vPlace[2], "score": 0.9},
                    }
                ]
                if vPlace
                else []
            )
        }

    monkeypatch.setattr(geocoding, "request_json", answer)

    return rQueries


def save_located_offers(pDatabaseFile, pLocations):
    """Enregistre une offre française par lieu, numérotée à partir de 1."""

    save_offers(
        pDatabaseFile,
        pd.DataFrame(
            [
                {
                    "source": "lever",
                    "source_id": str(vIndex),
                    "title": "Technicien",
                    "location": vLocation,
                    "country": "France",
                }
                for vIndex, vLocation in enumerate(pLocations, 1)
            ]
        ),
        NOW,
    )


def test_home_is_saved_then_cleared(tmp_path, geocoder):
    """Vérifie l'enregistrement du domicile, l'adresse introuvable et l'effacement."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)

    assert save_home(vDatabaseFile, " 59000   Lille ")["label"] == "Lille"
    assert load_home(vDatabaseFile)["latitude"] == 50.6366
    assert "type" not in geocoder[0]

    with pytest.raises(ValueError):
        save_home(vDatabaseFile, "Nulle part")

    assert save_home(vDatabaseFile, "") is None
    assert load_home(vDatabaseFile) is None


def test_offers_are_located_once_then_filtered_by_distance(tmp_path, geocoder):
    """Vérifie le placement des offres, le cache des lieux et le filtre de rayon."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    save_home(vDatabaseFile, "59000 Lille")
    save_located_offers(
        vDatabaseFile, ["Roubaix", "Lyon", "Roubaix", "France", "Atlantis"]
    )

    vReport = locate_offers(vDatabaseFile, NOW)

    assert vReport == {"located": 3, "lookups": 3, "unknown": 1}
    assert geocoder[1]["type"] == "municipality"
    assert geocoder[1]["lat"] == 50.6366
    assert get_cached_locations(vDatabaseFile)["atlantis"] is None

    assert locate_offers(vDatabaseFile, NOW)["lookups"] == 0

    vNear = {"latitude": 50.6366, "longitude": 3.0635, "radius_km": 25}

    assert sorted(get_offers(vDatabaseFile, pNear=vNear)["source_id"]) == ["1", "3"]


def test_location_stops_when_the_geocoder_fails(tmp_path, monkeypatch, caplog):
    """Vérifie qu'un géocodeur injoignable interrompt le passage sans erreur."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    save_located_offers(vDatabaseFile, ["Roubaix", "Lyon"])

    def fail(*_pArgs, **_pOptions):
        raise requests.ConnectionError("hors ligne")

    monkeypatch.setattr(geocoding, "request_json", fail)

    assert locate_offers(vDatabaseFile, NOW) == {
        "located": 0,
        "lookups": 0,
        "unknown": 0,
    }
    assert "reprise au prochain passage" in caplog.text


def test_lookups_are_capped_per_pass(tmp_path, geocoder):
    """Vérifie que les lieux au-delà du plafond attendent le passage suivant."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    save_located_offers(vDatabaseFile, ["Roubaix", "Lyon"])

    assert locate_offers(vDatabaseFile, NOW, pMaxLookups=1)["lookups"] == 1
    assert len(geocoder) == 1


@pytest.mark.parametrize(
    ("pKey", "pExpected"),
    [
        ("lille", True),
        ("", False),
        ("france", False),
        ("worldwide", False),
        ("puy de dome", False),
        ("59", False),
    ],
)
def test_is_locatable(pKey, pExpected):
    """Vérifie qu'un pays, une zone ou un département seul n'est pas cherché."""

    assert is_locatable(pKey) == pExpected
