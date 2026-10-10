"""Tests des méthodes utilitaires"""

from bs4 import BeautifulSoup
import pytest

from utils.helpers import (
    extract_price,
    extract_rating,
    extract_text,
    html_to_text,
    join_values,
    timestamp_to_iso,
)


def test_extract_text():
    """Vérifie l'extraction d'un texte HTML."""

    vHtml = "<h1>Développeur Python</h1>"
    vSoup = BeautifulSoup(vHtml, "html.parser")

    rText = extract_text(vSoup, "h1")

    assert rText == "Développeur Python"


def test_extract_text_returns_empty_string_when_element_is_missing():
    """Vérifie le comportement lorsqu'un élément est absent."""

    vHtml = "<h1>Développeur Python</h1>"
    vSoup = BeautifulSoup(vHtml, "html.parser")

    rText = extract_text(vSoup, ".company")

    assert rText == ""


def test_extract_price():
    """Vérifie la conversion d'un prix en valeur numérique."""

    rPrice = extract_price("£51.77")

    assert rPrice == 51.77


def test_extract_rating():
    """Vérifie la conversion d'une note."""

    vHtml = '<p class="star-rating Three"></p>'
    vSoup = BeautifulSoup(vHtml, "html.parser")

    rRating = extract_rating(vSoup.select_one(".star-rating"))

    assert rRating == 3


def test_extract_price_returns_zero_when_value_is_missing():
    """Vérifie le comportement lorsqu'un prix est absent."""

    rPrice = extract_price("")

    assert rPrice == 0.0


def test_extract_rating_returns_zero_when_element_is_missing():
    """Vérifie le comportement lorsqu'une note est absente."""

    rRating = extract_rating(None)

    assert rRating == 0


def test_extract_rating_returns_zero_when_rating_is_unknown():
    """Vérifie le comportement lorsqu'une note est inconnue."""

    vHtml = '<p class="star-rating Unknown"></p>'
    vSoup = BeautifulSoup(vHtml, "html.parser")

    rRating = extract_rating(vSoup.select_one(".star-rating"))

    assert rRating == 0


def test_extract_price_raises_error_when_value_is_invalid():
    """Vérifie qu'un prix invalide provoque une erreur."""

    with pytest.raises(ValueError):
        extract_price("£abc")


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
