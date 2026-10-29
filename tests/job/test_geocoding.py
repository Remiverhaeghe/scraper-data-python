"""Tests de la position du domicile et des offres"""

from datetime import datetime

import pandas as pd
import pytest
import requests

import job.geocoding as geocoding
from job.geocoding import (
    add_distances,
    compute_distance_km,
    describe_distance,
    describe_location,
    estimate_drive_minutes,
    get_home_department,
    read_postcode_department,
    is_locatable,
    keep_within_alert_radius,
    load_home,
    resolve_place,
    geocode_location,
    list_unknown_places,
    locate_all_offers,
    locate_new_offers,
    locate_offers,
    save_alert_radius,
    save_home,
)
from storage.database import initialize_database
from storage.geo_cache import (
    get_cached_departments,
    get_cached_locations,
    save_location,
)
from storage.job_offers import get_offers, save_offers

# Positions renvoyées par le géocodeur simulé, avec leur libellé
PLACES = {
    "59000 Lille": (50.6366, 3.0635, "Lille", "59, Nord, Hauts-de-France"),
    "Roubaix": (50.6942, 3.1746, "Roubaix", "59, Nord, Hauts-de-France"),
    "Lyon": (45.758, 4.835, "Lyon", "69, Rhône, Auvergne-Rhône-Alpes"),
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
                        "properties": {
                            "label": vPlace[2],
                            "score": 0.9,
                            "context": vPlace[3],
                        },
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


def test_new_offers_are_located_by_batch_with_a_home(tmp_path, geocoder, monkeypatch):
    """Vérifie le lot de fin de recherche : rien sans domicile, plafond sinon."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    save_located_offers(vDatabaseFile, ["Roubaix", "Lyon"])

    assert locate_new_offers(vDatabaseFile, NOW) is None

    save_home(vDatabaseFile, "59000 Lille")
    monkeypatch.setattr(geocoding, "BATCH_LOOKUPS", 1)

    assert locate_new_offers(vDatabaseFile, NOW)["lookups"] == 1
    assert locate_new_offers(vDatabaseFile, NOW)["lookups"] == 1


def test_all_offers_are_located_pass_after_pass(tmp_path, geocoder, monkeypatch):
    """Vérifie l'enchaînement des passages jusqu'au dernier lieu."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    save_located_offers(vDatabaseFile, ["Roubaix", "Lyon", "Brest"])
    monkeypatch.setattr(geocoding, "MAX_LOOKUPS", 2)

    vReport = locate_all_offers(vDatabaseFile, NOW)

    assert vReport["lookups"] == 3
    assert len(geocoder) == 3


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


def test_compute_distance_km():
    """Vérifie la distance Lille-Paris, environ 204 km à vol d'oiseau."""

    assert round(compute_distance_km((50.6366, 3.0635), (48.8566, 2.3522))) == 204


def test_distances_are_added_and_described():
    """Vérifie la distance au domicile, absente sans position ni domicile."""

    vHome = {"latitude": 50.6366, "longitude": 3.0635}
    vOffers = [
        {"location": "Roubaix", "latitude": 50.6942, "longitude": 3.1746},
        {"location": "France", "latitude": float("nan"), "longitude": None},
    ]

    add_distances(vOffers, vHome)

    assert [vOffer["distance_km"] for vOffer in vOffers] == [10, None]
    assert describe_location(vOffers[0]) == "Roubaix · 10 km"
    assert describe_location(vOffers[1]) == "France"
    assert describe_location({}) == ""

    add_distances(vOffers, None)

    assert vOffers[0]["distance_km"] is None


def test_alert_radius_keeps_near_and_remote_offers(tmp_path, geocoder):
    """Vérifie le rayon des alertes, gardé quand l'adresse change."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)

    with pytest.raises(ValueError):
        save_alert_radius(vDatabaseFile, 25)

    save_home(vDatabaseFile, "59000 Lille")
    save_alert_radius(vDatabaseFile, 25)
    save_home(vDatabaseFile, "Roubaix")
    vHome = load_home(vDatabaseFile)

    assert vHome["alert_radius_km"] == 25
    assert geocoder

    vOffers = [
        {"id": "proche", "distance_km": 10},
        {"id": "loin", "distance_km": 200},
        {"id": "inconnue", "distance_km": None},
        {"id": "teletravail", "distance_km": None, "remote": True},
    ]

    assert [vOffer["id"] for vOffer in keep_within_alert_radius(vOffers, vHome)] == [
        "proche",
        "teletravail",
    ]
    assert len(keep_within_alert_radius(vOffers, None)) == 4

    save_alert_radius(vDatabaseFile, 33)

    assert load_home(vDatabaseFile)["alert_radius_km"] == 0


def test_department_is_kept_and_old_places_are_looked_up_once(tmp_path, geocoder):
    """Vérifie le département de l'offre placée et la reprise des anciens lieux."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    save_located_offers(vDatabaseFile, ["Roubaix", "Lyon"])
    # Lieu cherché avant que le département soit gardé
    save_location(vDatabaseFile, "lyon", (45.758, 4.835), "Lyon", NOW)

    vReport = locate_offers(vDatabaseFile, NOW)
    vDepartments = {
        vOffer["location"]: vOffer["french_department"]
        for vOffer in get_offers(vDatabaseFile).to_dict("records")
    }

    assert vReport["lookups"] == 2
    assert vDepartments == {"Roubaix": "59", "Lyon": "69"}
    assert get_cached_departments(vDatabaseFile)["lyon"] == "69"
    assert locate_offers(vDatabaseFile, NOW)["lookups"] == 0


def test_city_alone_is_tried_when_the_full_place_is_unknown(geocoder):
    """Vérifie l'essai de la ville seule quand « Ville, Région, Pays » échoue."""

    vPlace = geocode_location("Roubaix, Hauts-de-France, France")

    assert vPlace[1] == "Roubaix"
    assert [vQuery["q"] for vQuery in geocoder] == [
        "Roubaix, Hauts-de-France, France",
        "Roubaix",
    ]


def test_postal_address_is_found_by_its_postcode_and_city(geocoder):
    """Vérifie qu'une adresse complète se cherche par « code postal commune »."""

    vPlace = geocode_location("12 rue de l'Usine 59000 Lille")

    assert vPlace[1] == "Lille"
    assert [vQuery["q"] for vQuery in geocoder][-1] == "59000 Lille"


def test_unknown_places_are_listed_then_resolved(tmp_path, geocoder):
    """Vérifie la liste des lieux introuvables, puis leur commune indiquée à la main."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    save_located_offers(vDatabaseFile, ["Atlantis", "Atlantis", "Lyon"])
    locate_offers(vDatabaseFile, NOW)

    vPlaces = list_unknown_places(vDatabaseFile)

    assert [(vPlace["example"], vPlace["count"]) for vPlace in vPlaces] == [
        ("Atlantis", 2)
    ]

    assert resolve_place(vDatabaseFile, "atlantis", "Roubaix", NOW) == "Roubaix"
    assert list_unknown_places(vDatabaseFile) == []

    with pytest.raises(ValueError):
        resolve_place(vDatabaseFile, "ailleurs", "Nulle part", NOW)


def test_drive_time_is_estimated_and_grows_with_distance():
    """Vérifie l'estimation du trajet : arrondie à 5 min, croissante, affichée."""

    vMinutes = [estimate_drive_minutes(vKm) for vKm in range(0, 150)]

    assert all(vFirst <= vSecond for vFirst, vSecond in zip(vMinutes, vMinutes[1:]))
    assert estimate_drive_minutes(0) == 5
    assert estimate_drive_minutes(20) == 40
    assert describe_distance({"distance_km": 20, "drive_minutes": 40}) == (
        "20 km · ≈ 40 min"
    )
    assert describe_distance({"distance_km": None}) == ""


def test_home_department_is_kept_or_read_in_the_postcode(tmp_path, geocoder):
    """Vérifie le département du domicile : gardé, sinon lu dans le code postal."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)

    assert get_home_department(vDatabaseFile) is None

    save_home(vDatabaseFile, "59000 Lille")

    assert get_home_department(vDatabaseFile) == "59"
    assert read_postcode_department("97400") == "974"
    assert read_postcode_department("20000") is None
