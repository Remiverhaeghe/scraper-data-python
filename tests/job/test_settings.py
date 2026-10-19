"""Tests des réglages de calcul partagés par le bureau et le web"""

from datetime import datetime

import pandas as pd
import pytest

from job.settings import (
    get_net_ratio,
    get_tax_rate,
    load_settings,
    parse_setting,
    save_settings,
)
from storage.database import initialize_database
from storage.job_offers import get_offer, save_offers


@pytest.fixture
def database_file(tmp_path, monkeypatch):
    """Crée une base contenant une offre à 36 000 € brut par an."""

    monkeypatch.delenv("INCOME_TAX_RATE", raising=False)

    rDatabaseFile = tmp_path / "scraper.db"

    initialize_database(rDatabaseFile)

    save_offers(
        rDatabaseFile,
        pd.DataFrame(
            [
                {
                    "source": "adzuna",
                    "source_id": "1",
                    "salary_min": 36000,
                    "salary_max": 36000,
                    "salary_period": "year",
                    "salary_currency": "EUR",
                    "salary_net_monthly_min": 2250,
                }
            ]
        ),
        datetime(2026, 10, 10),
    )

    return rDatabaseFile


def test_load_settings_returns_defaults(database_file):
    """Vérifie les valeurs par défaut lorsqu'aucun réglage n'est enregistré."""

    assert load_settings(database_file) == {
        "net_salary_percent": 75,
        "income_tax_rate": 0,
        "new_offer_days": 3,
        "expiry_days": 30,
        "follow_up_days": 7,
        "challenge_wait_seconds": 30,
        "weekly_application_goal": 0,
    }


def test_default_tax_rate_comes_from_environment(database_file, monkeypatch):
    """Vérifie que INCOME_TAX_RATE sert de valeur par défaut à l'impôt."""

    monkeypatch.setenv("INCOME_TAX_RATE", "7,5")

    assert load_settings(database_file)["income_tax_rate"] == 7.5


@pytest.mark.parametrize(
    "pKey, pValue, pMessage",
    [
        ("new_offer_days", "0", "entre 1 et 30"),
        ("follow_up_days", "2.5", "nombre entier attendu"),
        ("net_salary_percent", "abc", "nombre attendu"),
    ],
)
def test_parse_setting_rejects_invalid_values(pKey, pValue, pMessage):
    """Vérifie le refus des saisies hors bornes, non entières ou non numériques."""

    with pytest.raises(ValueError, match=pMessage):
        parse_setting(pKey, pValue)


def test_parse_setting_accepts_decimal_comma():
    """Vérifie qu'un taux saisi avec une virgule est accepté."""

    assert parse_setting("income_tax_rate", "7,5") == 7.5


def test_save_settings_recomputes_net_salaries(database_file):
    """Vérifie l'enregistrement et le recalcul du net des offres en base."""

    vSettings, vRecomputed = save_settings(
        database_file, {"net_salary_percent": "80", "income_tax_rate": "10"}
    )

    vOffer = get_offer(database_file, "adzuna", "1")

    assert vRecomputed == 1
    assert get_net_ratio(vSettings) == 0.8
    assert get_tax_rate(vSettings) == 10
    assert vOffer["salary_net_monthly_min"] == 2400
    assert vOffer["salary_net_after_tax_monthly_min"] == 2160
    assert load_settings(database_file)["net_salary_percent"] == 80


def test_save_settings_without_salary_change_skips_recompute(database_file):
    """Vérifie qu'un délai modifié ne recalcule pas les salaires."""

    _, vRecomputed = save_settings(database_file, {"follow_up_days": "10"})

    assert vRecomputed == 0


def test_save_settings_saves_nothing_when_a_value_is_invalid(database_file):
    """Vérifie qu'une seule erreur empêche tout enregistrement."""

    with pytest.raises(ValueError, match="Nouvelle offre"):
        save_settings(database_file, {"follow_up_days": "10", "new_offer_days": "99"})

    assert load_settings(database_file)["follow_up_days"] == 7


def test_zero_tax_rate_means_no_deduction():
    """Vérifie qu'un taux nul désactive la déduction de l'impôt."""

    assert get_tax_rate({"income_tax_rate": 0}) is None
