"""
Tests des arguments de ligne de commande.
"""

from unittest.mock import patch

from cli.arguments import parse_arguments


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