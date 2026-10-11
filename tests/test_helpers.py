"""Tests des méthodes utilitaires"""

import pytest

from utils.helpers import (
    decode_unicode_escapes,
    html_to_text,
    join_values,
    timestamp_to_iso,
)


def test_html_to_text():
    """Vérifie la conversion d'un contenu HTML en texte brut."""

    assert html_to_text("<h2>Poste</h2><p>Développeur <b>Python</b></p>") == (
        "Poste Développeur Python"
    )


def test_html_to_text_decodes_escaped_html():
    """Vérifie la conversion d'un HTML échappé par la source."""

    assert html_to_text("&lt;p&gt;Poste &lt;b&gt;Python&lt;/b&gt;&lt;/p&gt;") == (
        "Poste Python"
    )


def test_html_to_text_keeps_comparison_signs():
    """Vérifie qu'un texte contenant des comparaisons n'est pas altéré."""

    assert html_to_text("<p>Expérience &lt; 3 ans</p>") == "Expérience < 3 ans"


@pytest.mark.parametrize("pHtml", [None, ""])
def test_html_to_text_without_content(pHtml):
    """Vérifie qu'un contenu vide ne produit pas de texte."""

    assert html_to_text(pHtml) is None


@pytest.mark.parametrize(
    "pTimestamp, pExpected",
    [
        (1791622873, "2026-10-10T09:01:13+00:00"),
        ("1791622873", "2026-10-10T09:01:13+00:00"),
        (None, None),
    ],
)
def test_timestamp_to_iso(pTimestamp, pExpected):
    """Vérifie la conversion d'un horodatage Unix en date ISO."""

    assert timestamp_to_iso(pTimestamp) == pExpected


@pytest.mark.parametrize(
    "pValues, pExpected",
    [
        (["Full-Time", "Contract"], "Full-Time, Contract"),
        ("Senior", "Senior"),
        ([], None),
        (None, None),
    ],
)
def test_join_values(pValues, pExpected):
    """Vérifie le regroupement d'une liste de valeurs en texte."""

    assert join_values(pValues) == pExpected


@pytest.mark.parametrize(
    ("pText", "pExpected"),
    [
        (None, None),
        ("", ""),
        ("Syst\\u00e8mes d\\u2019Information", "Systèmes d’Information"),
        ("d\\u00E9j\\u00e0 vu", "déjà vu"),
        ("demi \\ud83d codet", "demi \\ud83d codet"),
        ("chemin C:\\users", "chemin C:\\users"),
    ],
)
def test_decode_unicode_escapes(pText, pExpected):
    """Vérifie le décodage des séquences unicode laissées dans le texte."""

    assert decode_unicode_escapes(pText) == pExpected
