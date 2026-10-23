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


def test_public_host_replaces_the_listening_address(monkeypatch):
    """Vérifie que le nom public, celui de Tailscale par exemple, sert à l'adresse."""

    monkeypatch.setenv("WEB_HOST", "0.0.0.0")
    monkeypatch.setenv("WEB_PUBLIC_HOST", "pc.tailnet.ts.net")
    monkeypatch.setenv("WEB_TLS_CERTFILE", "cert.pem")
    monkeypatch.setenv("WEB_TLS_KEYFILE", "key.pem")

    try:
        assert importlib.reload(config).WEB_BASE_URL == "https://pc.tailnet.ts.net:8000"

    finally:
        monkeypatch.undo()
        importlib.reload(config)
