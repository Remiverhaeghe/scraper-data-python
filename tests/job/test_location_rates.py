"""Tests du pays déduit du lieu et de la conversion des salaires en euros"""

from datetime import datetime, timedelta

import pandas as pd
import pytest

import job.exchange_rates as exchange_rates
from job.exchange_rates import get_exchange_rates, parse_ecb_rates
from job.location import add_location, detect_location
from job.presentation import format_euros, format_net_salary
from job.salary import add_net_salary
from storage.database import initialize_database

NOW = datetime(2026, 10, 11, 10, 0)

ECB_SAMPLE = """<Cube time='2026-10-09'>
<Cube currency='USD' rate='1.1206'/>
<Cube currency='GBP' rate='0.84763'/>
</Cube>"""


@pytest.mark.parametrize(
    "pLocation, pCountry, pExpected",
    [
        ("Lille", None, ("France", "Lille")),
        ("59000 Lille", None, ("France", "Lille")),
        ("Lille, Hauts-de-France", None, ("France", "Lille")),
        ("Paris (75)", None, ("France", "Paris")),
        ("France", None, ("France", None)),
        ("Berlin", None, ("Allemagne", "Berlin")),
        ("London, UK", None, ("Royaume-Uni", "London")),
        ("France, Japan, Turkey", None, (None, None)),
        ("Worldwide", None, (None, None)),
        ("Remote", None, (None, None)),
        (None, "FR", ("France", None)),
    ],
)
def test_detect_location(pLocation, pCountry, pExpected):
    """Vérifie le pays et la ville déduits du lieu."""

    assert detect_location(pLocation, pCountry) == pExpected


def test_add_location_keeps_source_values():
    """Vérifie que le pays et la ville fournis par la source sont conservés."""

    vItems = add_location(
        pd.DataFrame(
            [
                {"location": "Lille", "country": None, "city": None},
                {"location": "Lille", "country": "Belgique", "city": "Gand"},
            ]
        )
    )

    assert list(vItems["country"]) == ["France", "Belgique"]
    assert list(vItems["city"]) == ["Lille", "Gand"]


def test_parse_and_cache_rates(tmp_path, monkeypatch):
    """Vérifie la lecture du fichier de la BCE et le rafraîchissement hebdomadaire."""

    vDatabaseFile = tmp_path / "scraper.db"

    initialize_database(vDatabaseFile)

    assert parse_ecb_rates(ECB_SAMPLE) == {"USD": 1.1206, "GBP": 0.84763, "EUR": 1.0}

    vCalls = []

    def fake_fetch():
        """Simule un téléchargement réussi."""
        vCalls.append(True)

        return parse_ecb_rates(ECB_SAMPLE), "2026-10-09"

    monkeypatch.setattr(exchange_rates, "fetch_ecb_rates", fake_fetch)

    assert get_exchange_rates(vDatabaseFile, NOW)["USD"] == 1.1206
    assert get_exchange_rates(vDatabaseFile, NOW + timedelta(days=3))["USD"] == 1.1206
    assert len(vCalls) == 1

    def fail():
        """Simule un réseau coupé."""
        raise OSError("réseau coupé")

    monkeypatch.setattr(exchange_rates, "fetch_ecb_rates", fail)

    # Taux trop anciens et réseau coupé : les derniers taux connus servent.
    assert get_exchange_rates(vDatabaseFile, NOW + timedelta(days=10))["GBP"] == 0.84763


def test_net_salary_converted_from_dollars():
    """Vérifie le net estimé d'un salaire en dollars et son affichage approché."""

    vItems = add_net_salary(
        pd.DataFrame(
            [
                {
                    "salary_min": 112060,
                    "salary_max": None,
                    "salary_currency": "USD",
                    "salary_period": "year",
                },
                {
                    "salary_min": 50000,
                    "salary_max": None,
                    "salary_currency": "CHF",
                    "salary_period": "year",
                },
            ]
        ),
        pNetRatio=0.78,
        pRates={"USD": 1.1206},
    )

    vOffer = vItems.iloc[0].to_dict()

    assert vOffer["salary_net_monthly_min"] == 6500
    assert format_net_salary(vOffer) == f"≈ {format_euros(6500)} (USD)"
    assert pd.isna(vItems.iloc[1]["salary_net_monthly_min"])
