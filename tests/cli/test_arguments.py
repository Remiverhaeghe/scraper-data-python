"""Tests de la gestion des arguments de ligne de commande"""

from unittest.mock import patch

import pytest

from cli.arguments import parse_arguments


def test_parse_arguments_default_values():
    """Vérifie les valeurs par défaut des arguments."""

    with patch("sys.argv", ["main.py"]):
        vArguments = parse_arguments()

    assert vArguments.max_items is None
    assert vArguments.delay == 0.0
    assert vArguments.timeout == 10
    assert vArguments.max_pages is None
    assert vArguments.keyword is None


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


def test_parse_arguments_job_source(monkeypatch):
    """Vérifie qu'une seule source d'emploi peut être sélectionnée"""

    monkeypatch.setattr("sys.argv", ["main.py", "--source", "france-travail"])

    vArguments = parse_arguments()

    assert vArguments.sources == ["france-travail"]


def test_parse_arguments_multiple_job_sources(monkeypatch):
    """Vérifie que plusieurs sources d'emploi peuvent être sélectionnées"""
    monkeypatch.setattr(
        "sys.argv",
        [
            "main.py",
            "--source",
            "france-travail",
            "--source",
            "greenhouse",
            "--source",
            "remotive",
        ],
    )

    vArguments = parse_arguments()

    assert vArguments.sources == ["france-travail", "greenhouse", "remotive"]


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
