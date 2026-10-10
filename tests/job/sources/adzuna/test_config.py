"""Tests de la configuration Adzuna"""

import pytest

from job.sources.adzuna.config import load_config


def test_load_config(monkeypatch):
    """Vérifie le chargement des identifiants depuis l'environnement."""

    monkeypatch.setenv("ADZUNA_APP_ID", "test-id")
    monkeypatch.setenv("ADZUNA_APP_KEY", "test-key")

    rConfig = load_config()

    assert rConfig.app_id == "test-id"
    assert rConfig.app_key == "test-key"
    assert rConfig.country == "fr"


def test_load_config_lists_missing_variables(monkeypatch):
    """Vérifie que l'erreur nomme les variables manquantes."""

    monkeypatch.delenv("ADZUNA_APP_ID", raising=False)
    monkeypatch.delenv("ADZUNA_APP_KEY", raising=False)

    with pytest.raises(ValueError, match="ADZUNA_APP_ID, ADZUNA_APP_KEY"):
        load_config()
