"""
Tests des arguments de ligne de commande.
"""

from unittest.mock import patch

import pytest

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


def test_min_rating_accepts_minimum_value(monkeypatch):
    """Vérifie que la note minimale configurée est acceptée."""

    monkeypatch.setattr(
        "sys.argv",
        ["main.py", "--min-rating", "1"]
    )

    arguments = parse_arguments()

    assert arguments.min_rating == 1


def test_min_rating_accepts_maximum_value(monkeypatch):
    """Vérifie que la note maximale configurée est acceptée."""

    monkeypatch.setattr(
        "sys.argv",
        ["main.py", "--min-rating", "5"]
    )

    arguments = parse_arguments()

    assert arguments.min_rating == 5

def test_min_rating_rejects_value_below_minimum(monkeypatch):
    """Vérifie qu'une note inférieure au minimum est refusée."""

    monkeypatch.setattr(
        "sys.argv",
        ["main.py", "--min-rating", "0"]
    )

    with pytest.raises(SystemExit):
        parse_arguments()

def test_min_rating_rejects_value_above_maximum(monkeypatch):
    """Vérifie qu'une note supérieure au maximum est refusée."""

    monkeypatch.setattr(
        "sys.argv",
        ["main.py", "--min-rating", "6"]
    )

    with pytest.raises(SystemExit):
        parse_arguments()

def test_parse_arguments_refresh(monkeypatch):
    """Vérifie que l'option --refresh est correctement analysée."""

    monkeypatch.setattr(
        "sys.argv",
        ["main.py", "--refresh"]
    )

    arguments = parse_arguments()

    assert arguments.refresh is True


def test_parse_arguments_without_refresh(monkeypatch):
    """Vérifie que --refresh est désactivé par défaut."""

    monkeypatch.setattr(
        "sys.argv",
        ["main.py"]
    )

    arguments = parse_arguments()

    assert arguments.refresh is False