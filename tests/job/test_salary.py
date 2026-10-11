"""Tests de l'estimation du salaire net mensuel"""

import pandas as pd
import pytest

from job.salary import (
    add_net_salary,
    assume_euro_in_france,
    get_income_tax_rate,
    is_located_in_france,
    to_net_monthly,
)


def build_items(pAmount, pPeriod, pCurrency="EUR"):
    """Construit un DataFrame contenant une offre avec un salaire brut."""

    rItems = pd.DataFrame(
        [
            {
                "salary_min": pAmount,
                "salary_max": None,
                "salary_currency": pCurrency,
                "salary_period": pPeriod,
            }
        ]
    )

    return rItems


@pytest.mark.parametrize(
    "pAmount, pPeriod, pExpected",
    [(48000, "year", 3000), (4000, "month", 3000), (20, "hour", 2275)],
)
def test_to_net_monthly_converts_each_period(pAmount, pPeriod, pExpected):
    """Vérifie la conversion en net mensuel selon la période du brut."""

    assert to_net_monthly(pAmount, pPeriod, 0.75) == pExpected


def test_to_net_monthly_ignores_unknown_period():
    """Vérifie qu'une période inconnue ne produit pas de net."""

    assert to_net_monthly(48000, None, 0.75) is None


def test_to_net_monthly_ignores_implausible_amount():
    """Vérifie qu'un taux journalier présenté comme annuel est ignoré."""

    assert to_net_monthly(360, "year", 0.75) is None


def test_add_net_salary_without_tax_rate():
    """Vérifie le calcul du net sans taux d'imposition renseigné."""

    rItems = add_net_salary(build_items(48000, "year"), pNetRatio=0.75)

    assert rItems.loc[0, "salary_net_monthly_min"] == 3000
    assert pd.isna(rItems.loc[0, "salary_net_monthly_max"])
    assert pd.isna(rItems.loc[0, "salary_net_after_tax_monthly_min"])


def test_add_net_salary_with_tax_rate():
    """Vérifie le calcul du net après impôt lorsqu'un taux est fourni."""

    rItems = add_net_salary(build_items(48000, "year"), pNetRatio=0.75, pTaxRate=10)

    assert rItems.loc[0, "salary_net_after_tax_monthly_min"] == 2700


def test_add_net_salary_ignores_other_currencies():
    """Vérifie qu'un salaire hors euros n'est pas converti."""

    rItems = add_net_salary(build_items(48000, "year", "USD"), pNetRatio=0.75)

    assert pd.isna(rItems.loc[0, "salary_net_monthly_min"])


def test_get_income_tax_rate_is_optional(monkeypatch):
    """Vérifie qu'aucun taux n'est appliqué si la variable est absente."""

    monkeypatch.delenv("INCOME_TAX_RATE", raising=False)

    assert get_income_tax_rate() is None


def test_get_income_tax_rate_accepts_comma(monkeypatch):
    """Vérifie la lecture d'un taux saisi avec une virgule."""

    monkeypatch.setenv("INCOME_TAX_RATE", "7,5")

    assert get_income_tax_rate() == 7.5


@pytest.mark.parametrize("pValue", ["abc", "150"])
def test_get_income_tax_rate_rejects_invalid_value(monkeypatch, pValue):
    """Vérifie le rejet d'un taux invalide."""

    monkeypatch.setenv("INCOME_TAX_RATE", pValue)

    with pytest.raises(ValueError, match="INCOME_TAX_RATE"):
        get_income_tax_rate()


def test_add_net_salary_logs_ignored_amounts_once(caplog):
    """Vérifie que les montants incohérents sont signalés en un seul message."""

    vItems = pd.concat(
        [
            build_items(360, "year"),
            build_items(450, "year"),
            build_items(48000, "year"),
        ],
        ignore_index=True,
    )

    add_net_salary(vItems, pNetRatio=0.75)

    vWarnings = [
        vRecord for vRecord in caplog.records if vRecord.levelname == "WARNING"
    ]

    assert len(vWarnings) == 1
    assert "2 salaire(s) ignoré(s)" in vWarnings[0].getMessage()


@pytest.mark.parametrize(
    "pLocation, pCountry, pExpected",
    [
        ("France", None, True),
        ("Lille, Hauts-de-France", None, True),
        ("59000 Lille", None, True),
        ("Paris (75)", None, True),
        ("France (Remote)", None, True),
        ("France, Japan, Turkey, Vietnam, Mexico, Norway", None, False),
        ("EMEA", None, False),
        ("Lille", None, False),
        (None, "France", True),
        ("Remote", "Germany", False),
    ],
)
def test_is_located_in_france(pLocation, pCountry, pExpected):
    """Vérifie la reconnaissance d'une offre située en France seulement."""

    assert is_located_in_france(pLocation, pCountry) is pExpected


def test_assume_euro_in_france():
    """Vérifie que seul un salaire en dollars ou sans devise d'une offre en France passe en euros."""

    vItems = pd.DataFrame(
        [
            {"location": "France", "salary_min": 60000, "salary_currency": "USD"},
            {"location": "France", "salary_min": 40000, "salary_currency": None},
            {"location": "France", "salary_min": 50000, "salary_currency": "GBP"},
            {"location": "France", "salary_min": None, "salary_currency": "USD"},
            {"location": "Worldwide", "salary_min": 90000, "salary_currency": "USD"},
        ]
    )

    vCurrencies = list(assume_euro_in_france(vItems)["salary_currency"])

    assert vCurrencies[:3] == ["EUR", "EUR", "GBP"]
    assert vCurrencies[3:] == ["USD", "USD"]
