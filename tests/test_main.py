"""
Tests du point d'entrée de l'application.
"""

from unittest.mock import patch

from main import parse_arguments


def test_parse_arguments_without_max_pages():
    """Vérifie l'absence de limite par défaut."""

    with patch(
        "sys.argv",
        ["main.py"]
    ):
        arguments = parse_arguments()

    assert arguments.max_pages is None


def test_parse_arguments_with_max_pages():
    """Vérifie la récupération du nombre maximum de pages."""

    with patch(
        "sys.argv",
        ["main.py", "--max-pages", "2"]
    ):
        arguments = parse_arguments()

    assert arguments.max_pages == 2