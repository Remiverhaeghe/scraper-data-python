"""Tests de la configuration générale de l'application"""

import importlib

import pytest

import config
from config import DATABASE_FILE


def test_database_file_is_configured():
    """Vérifie que le chemin de la base SQLite est configuré."""

    assert DATABASE_FILE == "data/scraper.db"


@pytest.mark.parametrize(
    "pValue, pExpected", [("", "127.0.0.1"), ("192.168.1.80", "192.168.1.80")]
)
def test_web_host_defaults_to_this_computer(monkeypatch, pValue, pExpected):
    """Vérifie l'écoute locale par défaut, et l'adresse choisie dans .env sinon.

    La variable est fixée avant le rechargement : load_dotenv ne remplace pas une
    variable déjà définie, le .env du poste n'influence donc pas le test.
    """

    monkeypatch.setenv("WEB_HOST", pValue)

    try:
        assert importlib.reload(config).WEB_HOST == pExpected

    finally:
        monkeypatch.undo()
        importlib.reload(config)
