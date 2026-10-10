"""Tests de la détection des avantages salariaux"""

import pandas as pd
import pytest

from job.benefits import add_benefits, detect_benefits


@pytest.mark.parametrize(
    "pText, pColumn",
    [
        ("Salaire versé sur 13 mois", "has_13th_month"),
        ("Mensuel de 2500 Euros sur 13.0 mois", "has_13th_month"),
        ("13ème mois et tickets restaurant", "has_13th_month"),
        ("Primes trimestrielles", "has_bonus"),
        ("Part variable selon objectifs", "has_bonus"),
        ("Intéressement et participation", "has_profit_sharing"),
        ("Participation aux bénéfices", "has_profit_sharing"),
        ("PEE abondé et PERCOL", "has_savings_plan"),
        ("Plan d'épargne : PER collectif", "has_savings_plan"),
        ("Accès à l'épargne salariale", "has_savings_plan"),
    ],
)
def test_detect_benefits_finds_mentions(pText, pColumn):
    """Vérifie la détection de chaque avantage."""

    assert detect_benefits(pText)[pColumn] is True


@pytest.mark.parametrize(
    "pText",
    [
        "Participation aux projets de l'équipe",
        "Manipulation de variables Python",
        "Exprimer ses idées",
        "Expérience de 13 ans minimum",
    ],
)
def test_detect_benefits_ignores_ambiguous_words(pText):
    """Vérifie l'absence de faux positif sur des formulations courantes."""

    assert all(vValue is None for vValue in detect_benefits(pText).values())


def test_add_benefits_scans_all_text_columns():
    """Vérifie que le titre, le libellé de salaire et la description sont analysés."""

    vItems = pd.DataFrame(
        [
            {
                "title": "Développeur Python",
                "salary_label": "Mensuel de 3000 Euros sur 13 mois | Primes",
                "description": "Intéressement et PEE",
            },
            {"title": "Développeur Java", "salary_label": None, "description": None},
        ]
    )

    rItems = add_benefits(vItems)

    assert rItems.loc[0, "has_13th_month"] is True
    assert rItems.loc[0, "has_bonus"] is True
    assert rItems.loc[0, "has_profit_sharing"] is True
    assert rItems.loc[0, "has_savings_plan"] is True
    assert rItems.loc[1, "has_13th_month"] is None


def test_add_benefits_with_empty_items():
    """Vérifie le traitement d'un résultat sans offre."""

    rItems = add_benefits(pd.DataFrame(columns=["title", "description"]))

    assert "has_bonus" in rItems.columns
    assert rItems.empty
