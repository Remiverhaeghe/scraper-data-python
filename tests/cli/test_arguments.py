"""Tests de la gestion des arguments de ligne de commande"""

from unittest.mock import patch

import pytest

from cli.arguments import parse_arguments


def test_parse_arguments_default_values():
    """Vérifie les valeurs par défaut des arguments."""

    with patch("sys.argv", ["main.py"]):
        vArguments = parse_arguments()

    assert vArguments.type == "book"
    assert vArguments.max_items is None
    assert vArguments.delay == 0.0
    assert vArguments.timeout == 10
    assert vArguments.max_pages is None
    assert vArguments.refresh is False
    assert vArguments.title is None
    assert vArguments.max_price is None
    assert vArguments.min_rating is None


def test_parse_arguments_common_configuration():
    """Vérifie la récupération des paramètres communs au scraping."""

    with patch(
        "sys.argv",
        ["main.py", "--max-items", "100", "--delay", "2.5", "--timeout", "30"],
    ):
        vArguments = parse_arguments()

    assert vArguments.max_items == 100
    assert vArguments.delay == 2.5
    assert vArguments.timeout == 30


def test_parse_arguments_book_configuration():
    """Vérifie la récupération des paramètres spécifiques aux livres."""

    with patch(
        "sys.argv",
        [
            "main.py",
            "--max-pages",
            "5",
            "--title",
            "Python",
            "--max-price",
            "50.0",
            "--min-rating",
            "4",
            "--refresh",
        ],
    ):
        vArguments = parse_arguments()

    assert vArguments.max_pages == 5
    assert vArguments.title == "Python"
    assert vArguments.max_price == 50.0
    assert vArguments.min_rating == 4
    assert vArguments.refresh is True


def test_parse_arguments_accepts_job(monkeypatch):
    """Vérifie que le scraping des offres d'emploi peut être sélectionné."""

    monkeypatch.setattr("sys.argv", ["main.py", "--type", "job"])

    vArguments = parse_arguments()

    assert vArguments.type == "job"


def test_parse_arguments_job_source(monkeypatch):
    """Vérifie qu'une seule source d'emploi peut être sélectionnée"""

    monkeypatch.setattr(
        "sys.argv", ["main.py", "--type", "job", "--source", "france-travail"]
    )

    vArguments = parse_arguments()

    assert vArguments.sources == ["france-travail"]


def test_parse_arguments_multiple_job_sources(monkeypatch):
    """Vérifie que plusieurs sources d'emploi peuvent être sélectionnées"""
    monkeypatch.setattr(
        "sys.argv",
        [
            "main.py",
            "--type",
            "job",
            "--source",
            "france-travail",
            "--source",
            "greenhouse",
            "--source",
            "lever",
        ],
    )

    vArguments = parse_arguments()

    assert vArguments.sources == ["france-travail", "greenhouse", "lever"]


def test_parse_arguments_normalizes_contract():
    """Vérifie que le contrat est accepté quelle que soit la casse."""

    with patch("sys.argv", ["main.py", "--contract", "freelance"]):
        vArguments = parse_arguments()

    assert vArguments.contract == "FREELANCE"


def test_parse_arguments_rejects_unknown_contract():
    """Vérifie le rejet d'un type de contrat inconnu."""

    with patch("sys.argv", ["main.py", "--contract", "stage"]):
        with pytest.raises(SystemExit):
            parse_arguments()
