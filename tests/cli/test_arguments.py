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


def test_parse_arguments_with_title(monkeypatch):
    """Vérifie la récupération du titre recherché."""

    monkeypatch.setattr(
        "sys.argv",
        ["main.py", "--title", "python"]
    )

    arguments = parse_arguments()

    assert arguments.title == "python"


def test_parse_arguments_with_max_price(monkeypatch):
    """Vérifie la récupération du prix maximum."""

    monkeypatch.setattr(
        "sys.argv",
        ["main.py", "--max-price", "20"]
    )

    arguments = parse_arguments()

    assert arguments.max_price == 20.0


def test_parse_arguments_with_min_rating(monkeypatch):
    """Vérifie la récupération de la note minimum."""

    monkeypatch.setattr(
        "sys.argv",
        ["main.py", "--min-rating", "4"]
    )

    arguments = parse_arguments()

    assert arguments.min_rating == 4