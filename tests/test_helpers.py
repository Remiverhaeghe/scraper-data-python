# ============================================================================
# Tests des méthodes utilitaires
# ============================================================================


from bs4 import BeautifulSoup
import pytest

from utils.helpers import (
    extract_price,
    extract_rating,
    extract_text
)


def test_extract_text():
    """
    Vérifie l'extraction d'un texte HTML.
    """

    vHtml = "<h1>Développeur Python</h1>"
    vSoup = BeautifulSoup(
        vHtml,
        "html.parser"
    )

    rText = extract_text(
        vSoup,
        "h1"
    )

    assert rText == "Développeur Python"


def test_extract_text_returns_empty_string_when_element_is_missing():
    """
    Vérifie le comportement lorsqu'un élément est absent.
    """

    vHtml = "<h1>Développeur Python</h1>"
    vSoup = BeautifulSoup(
        vHtml,
        "html.parser"
    )

    rText = extract_text(
        vSoup,
        ".company"
    )

    assert rText == ""


def test_extract_price():
    """
    Vérifie la conversion d'un prix en valeur numérique.
    """

    rPrice = extract_price(
        "£51.77"
    )

    assert rPrice == 51.77


def test_extract_rating():
    """
    Vérifie la conversion d'une note.
    """

    vHtml = '<p class="star-rating Three"></p>'
    vSoup = BeautifulSoup(
        vHtml,
        "html.parser"
    )

    rRating = extract_rating(
        vSoup.select_one(".star-rating")
    )

    assert rRating == 3


def test_extract_price_returns_zero_when_value_is_missing():
    """
    Vérifie le comportement lorsqu'un prix est absent.
    """

    rPrice = extract_price(
        ""
    )

    assert rPrice == 0.0


def test_extract_rating_returns_zero_when_element_is_missing():
    """
    Vérifie le comportement lorsqu'une note est absente.
    """

    rRating = extract_rating(
        None
    )

    assert rRating == 0


def test_extract_rating_returns_zero_when_rating_is_unknown():
    """
    Vérifie le comportement lorsqu'une note est inconnue.
    """

    vHtml = '<p class="star-rating Unknown"></p>'
    vSoup = BeautifulSoup(
        vHtml,
        "html.parser"
    )

    rRating = extract_rating(
        vSoup.select_one(".star-rating")
    )

    assert rRating == 0


def test_extract_price_raises_error_when_value_is_invalid():
    """
    Vérifie qu'un prix invalide provoque une erreur.
    """

    with pytest.raises(ValueError):
        extract_price(
            "£abc"
        )