"""Tests des employeurs industriels de la région : secteurs, distance, suivi, offres"""

from datetime import date, datetime

import pandas as pd
import pytest
import requests

from job.companies import load_company_rules
from job.local_employers import (
    REGION_DEPARTMENTS,
    SECTIONS,
    build_employers_view,
    fetch_local_employers,
    follow_employer,
    get_sector,
    record_spontaneous,
)
from job.geocoding import HOME_KEY
from storage.database import initialize_database
from storage.job_offers import save_offers
from storage.settings_repository import save_json_setting

NOW = datetime(2026, 10, 31, 9, 0)
HOME = {"label": "Lille", "address": "Lille", "latitude": 50.63, "longitude": 3.06}


def make_result(pSiren, pName, pActivity, pLatitude, pSigle=None):
    """Retourne un résultat de l'annuaire avec un site ouvert."""

    rResult = {
        "siren": pSiren,
        "nom_complet": pName,
        "nom_raison_sociale": pName,
        "sigle": pSigle,
        "activite_principale": pActivity,
        "categorie_entreprise": "GE",
        "tranche_effectif_salarie": "42",
        "matching_etablissements": [
            {
                "latitude": str(pLatitude),
                "longitude": "3.06",
                "libelle_commune": "VILLE",
                "etat_administratif": "A",
            }
        ],
    }

    return rResult


@pytest.fixture
def database_file(tmp_path):
    """Fournit une base avec un domicile à Lille et une offre de Roquette."""

    rDatabaseFile = tmp_path / "scraper.db"
    initialize_database(rDatabaseFile)
    save_json_setting(rDatabaseFile, HOME_KEY, HOME)
    save_offers(
        rDatabaseFile,
        pd.DataFrame(
            [
                {
                    "source": "lever",
                    "source_id": "1",
                    "title": "Technicien",
                    "company": "Roquette Frères",
                }
            ]
        ),
        NOW,
    )

    return rDatabaseFile


@pytest.mark.parametrize(
    "pActivity, pSector",
    [
        ("10.62Z", "Agroalimentaire"),
        ("30.20Z", "Matériel de transport"),
        ("35.11Z", "Énergie"),
        ("23.63Z", "Autre industrie"),
        (None, "Autre industrie"),
    ],
)
def test_sector_comes_from_the_activity_code(pActivity, pSector):
    """Vérifie le secteur tiré des deux premiers chiffres du code NAF."""

    assert get_sector(pActivity) == pSector


def test_employers_are_fetched_sorted_followed_and_matched(database_file):
    """Vérifie la liste : pages parcourues, doublons, distance, offres, suivi."""

    vCalls = []

    def fake_request(_pMethod, _pUrl, pParams):
        vCalls.append(pParams)
        vResults = [
            make_result("1", "ROQUETTE FRERES", "10.62Z", 50.60),
            make_result("2", "ALSTOM TRANSPORT SA", "30.20Z", 50.35, "ALSTOM"),
        ]

        return {"total_pages": 2 if pParams["page"] == 1 else 2, "results": vResults}

    assert fetch_local_employers(database_file, NOW, fake_request, 0) == 2
    assert len(vCalls) == len(REGION_DEPARTMENTS) * len(SECTIONS) * 2

    vView = build_employers_view(database_file)

    assert [vItem["name"] for vItem in vView["employers"]] == [
        "ROQUETTE FRERES",
        "ALSTOM TRANSPORT SA",
    ]
    assert (
        vView["employers"][0]["offers"] == 1
        and vView["employers"][0]["distance_km"] < 10
    )
    assert [
        vItem["name"]
        for vItem in build_employers_view(database_file, "Agroalimentaire")["employers"]
    ] == ["ROQUETTE FRERES"]
    assert build_employers_view(database_file, pMaxDistance=10)["count"] == 2
    assert len(build_employers_view(database_file, pMaxDistance=10)["employers"]) == 1

    follow_employer(database_file, "2")

    assert set(load_company_rules(database_file)["preferred"]) == {
        "ALSTOM TRANSPORT SA",
        "ALSTOM",
    }
    assert build_employers_view(database_file)["employers"][1]["followed"]

    with pytest.raises(ValueError):
        follow_employer(database_file, "inconnu")


def test_unreachable_directory_keeps_the_previous_list(database_file):
    """Vérifie qu'une panne du service laisse la liste précédente en place."""

    def failing_request(*_pArgs, **_pOptions):
        raise requests.ConnectionError("hors ligne")

    with pytest.raises(ValueError, match="ne répond pas"):
        fetch_local_employers(database_file, NOW, failing_request, 0)

    assert build_employers_view(database_file)["count"] == 0


def test_spontaneous_applications_are_tracked_and_filtered(database_file):
    """Vérifie l'effectif, la position, l'envoi qui suit l'employeur et le filtre."""

    def fake_request(_pMethod, _pUrl, pParams):
        return {
            "total_pages": 1,
            "results": [
                make_result("1", "ROQUETTE FRERES", "10.62Z", 50.60),
                make_result("2", "ALSTOM TRANSPORT SA", "30.20Z", 50.35),
            ],
        }

    fetch_local_employers(database_file, NOW, fake_request, 0)
    record_spontaneous(database_file, "2", "sent", date(2026, 10, 1))

    vView = build_employers_view(database_file, pToday=date(2026, 10, 20))
    vAlstom = vView["employers"][1]

    assert vAlstom["headcount"] == "1 000 à 1 999 salariés"
    assert (vAlstom["latitude"], vAlstom["longitude"]) == (50.35, 3.06)
    assert vAlstom["followed"] and vAlstom["spontaneous"]["follow_up_due"]
    assert (vView["sent_count"], vView["due_count"]) == (1, 1)

    def names(pContact):
        return [
            vItem["name"]
            for vItem in build_employers_view(
                database_file, pContact=pContact, pToday=date(2026, 10, 20)
            )["employers"]
        ]

    assert names("todo") == ["ROQUETTE FRERES"]
    assert names("sent") == names("due") == ["ALSTOM TRANSPORT SA"]

    record_spontaneous(database_file, "1", "refused", date(2026, 10, 2))

    assert names("due") == ["ALSTOM TRANSPORT SA"]
    assert "ROQUETTE FRERES" not in load_company_rules(database_file)["preferred"]

    with pytest.raises(ValueError):
        record_spontaneous(database_file, "inconnu", "sent")
