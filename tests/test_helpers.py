"""
Tests des méthodes utilitaires.
"""

from bs4 import BeautifulSoup

from utils.helpers import extract_text


def test_extract_text():
    """Vérifie l'extraction d'un texte HTML."""

    html = "<h1>Développeur Python</h1>"
    soup = BeautifulSoup(html, "html.parser")

    result = extract_text(soup, "h1")

    assert result == "Développeur Python"

def test_extract_text_returns_empty_string_when_element_is_missing():
    """Vérifie le comportement lorsqu'un élément est absent."""

    html = "<h1>Développeur Python</h1>"
    soup = BeautifulSoup(html, "html.parser")

    result = extract_text(soup, ".company")

    assert result == ""   