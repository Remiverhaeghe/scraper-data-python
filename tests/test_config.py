"""Tests de la configuration générale de l'application"""

import importlib
from pathlib import Path

import pytest

import config
from config import DATABASE_FILE


def test_database_file_is_configured():
    """Vérifie que la base est rangée dans le dossier des données, hors du projet."""

    assert Path(DATABASE_FILE) == config.DATA_DIRECTORY / "scraper.db"
    assert config.EXPORTS_DIRECTORY.parent == config.DATA_DIRECTORY
    assert config.IMPORTS_DIRECTORY.parent == config.DATA_DIRECTORY
    assert Path(__file__).resolve().parents[1] not in config.DATA_DIRECTORY.parents


def test_data_directory_can_be_chosen(monkeypatch, tmp_path):
    """Vérifie que JOBBOARD_DATA_DIR déplace toutes les données (Docker : /app/data)."""

    monkeypatch.setenv("JOBBOARD_DATA_DIR", str(tmp_path))

    try:
        vConfig = importlib.reload(config)

        assert vConfig.DATABASE_FILE == str(tmp_path / "scraper.db")
        assert vConfig.QUIZ_PACKS_DIRECTORY == str(tmp_path / "packs")

    finally:
        # Dossier temporaire des tests rétabli (tests/conftest.py)
        monkeypatch.undo()
        importlib.reload(config)


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
