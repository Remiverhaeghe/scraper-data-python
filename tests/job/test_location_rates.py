"""Tests du pays déduit du lieu et de la conversion des salaires en euros"""

from datetime import datetime, timedelta

import pandas as pd
import pytest
import requests

import job.exchange_rates as exchange_rates
from job.exchange_rates import (
    fetch_ecb_rates,
    get_exchange_rates,
    load_stored_rates,
    parse_ecb_rates,
)
from job.location import (
    FRENCH_DEPARTMENTS,
    REGION_BY_DEPARTMENT,
    add_location,
    detect_location,
    find_region,
    find_region_in_text,
)
from job.presentation import format_euros, format_net_salary
from job.salary import add_net_salary
from storage.database import initialize_database
from storage.settings_repository import save_setting_values

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
        # Relevés dans la base : code postal allemand, mots parasites
        ("München (81671)", None, ("Allemagne", "München")),
        ("Nürnberg", None, ("Allemagne", "Nürnberg")),
        ("Paris Office", None, ("France", "Paris")),
        ("Zurich HQ", None, ("Suisse", "Zurich")),
        ("Remote in Deutschland", None, ("Allemagne", None)),
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


class FakeEcbResponse:
    """Réponse simulée de la BCE, lue par morceaux comme un flux HTTP."""

    headers = {}

    def __init__(self, pText):
        self.text = pText
        self.closed = False

    def raise_for_status(self):
        """Ne lève rien : réponse en succès."""

    def iter_content(self, chunk_size):
        """Restitue le texte en un seul morceau."""
        yield self.text.encode("utf-8")

    def close(self):
        """Note la fermeture de la réponse."""
        self.closed = True


def test_fetch_ecb_rates_reads_rates_and_date(monkeypatch):
    """Vérifie le téléchargement : taux, date de publication et réponse fermée."""

    vResponse = FakeEcbResponse(ECB_SAMPLE)

    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: vResponse)

    vRates, vPublishedOn = fetch_ecb_rates()

    assert vRates["USD"] == 1.1206
    assert vPublishedOn == "2026-10-09"
    assert vResponse.closed


def test_fetch_ecb_rates_refuses_a_file_without_rates(monkeypatch):
    """Vérifie qu'un fichier sans taux, page d'erreur par exemple, est refusé."""

    monkeypatch.setattr(
        requests, "get", lambda *args, **kwargs: FakeEcbResponse("<html></html>")
    )

    with pytest.raises(ValueError, match="Aucun taux"):
        fetch_ecb_rates()


def test_unreadable_stored_rates_are_refreshed(tmp_path, monkeypatch):
    """Vérifie que des taux enregistrés illisibles sont ignorés puis remplacés."""

    vDatabaseFile = tmp_path / "scraper.db"

    initialize_database(vDatabaseFile)
    save_setting_values(vDatabaseFile, {exchange_rates.RATES_KEY: "{pas du json"})

    assert load_stored_rates(vDatabaseFile) == ({}, None)

    monkeypatch.setattr(
        exchange_rates,
        "fetch_ecb_rates",
        lambda: (parse_ecb_rates(ECB_SAMPLE), "2026-10-09"),
    )

    assert get_exchange_rates(vDatabaseFile, NOW)["GBP"] == 0.84763


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


@pytest.mark.parametrize(
    ("pLocation", "pExpected"),
    [
        ("Pas-de-Calais, Hauts-De-France", "Hauts-de-France"),
        ("Cogolin, Var", "Provence-Alpes-Côte d'Azur"),
        ("Ardennes, Grand-Est", "Grand Est"),
        ("Paris", "Île-de-France"),
        ("Saint-Martin-d'Ain", None),
        ("France", None),
        (None, None),
    ],
)
def test_region_is_found_in_the_location(pLocation, pExpected):
    """Vérifie la région nommée dans un lieu, segment par segment."""

    assert find_region_in_text(pLocation) == pExpected


def test_every_department_has_a_region():
    """Vérifie la table des régions : chaque département en a une, et une seule."""

    assert set(REGION_BY_DEPARTMENT) == set(FRENCH_DEPARTMENTS)
    assert find_region("59") == "Hauts-de-France"
    assert find_region("2a") == "Corse"
    assert find_region("") is None


def test_country_code_given_by_the_source_is_renamed():
    """Vérifie qu'un pays donné en code (« FR ») prend son nom, comme un pays déduit."""

    vItems = add_location(
        pd.DataFrame(
            [
                {"location": "Hem", "country": "FR"},
                {"location": "Berlin", "country": "Germany"},
                {"location": "Lille", "country": None},
            ]
        )
    )

    assert vItems["country"].tolist() == ["France", "Allemagne", "France"]
