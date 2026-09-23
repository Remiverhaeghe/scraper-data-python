# ============================================================================
# Tests de la configuration France Travail
# ============================================================================

import pytest

from job.sources.france_travail.config import (
    FranceTravailConfig,
    load_config
)


def test_load_config(monkeypatch):
    """
    Vérifie le chargement complet de la configuration.
    """

    monkeypatch.setenv(
        "FRANCE_TRAVAIL_CLIENT_ID",
        "client-id"
    )

    monkeypatch.setenv(
        "FRANCE_TRAVAIL_CLIENT_SECRET",
        "client-secret"
    )

    monkeypatch.setenv(
        "FRANCE_TRAVAIL_SCOPE",
        "scope"
    )

    monkeypatch.setenv(
        "FRANCE_TRAVAIL_TOKEN_URL",
        "https://example.com/token"
    )

    monkeypatch.setenv(
        "FRANCE_TRAVAIL_API_BASE_URL",
        "https://example.com/api/"
    )

    rConfig = load_config()

    assert isinstance(
        rConfig,
        FranceTravailConfig
    )

    assert rConfig.client_id == "client-id"
    assert rConfig.client_secret == "client-secret"
    assert rConfig.scope == "scope"
    assert rConfig.token_url == "https://example.com/token"
    assert rConfig.api_base_url == "https://example.com/api/"


def test_load_config_missing_client_id(monkeypatch):
    """
    Vérifie qu'une erreur est levée lorsque le client ID est absent.
    """

    monkeypatch.delenv(
        "FRANCE_TRAVAIL_CLIENT_ID",
        raising=False
    )

    monkeypatch.setenv(
        "FRANCE_TRAVAIL_CLIENT_SECRET",
        "client-secret"
    )

    monkeypatch.setenv(
        "FRANCE_TRAVAIL_SCOPE",
        "scope"
    )

    monkeypatch.setenv(
        "FRANCE_TRAVAIL_TOKEN_URL",
        "https://example.com/token"
    )

    monkeypatch.setenv(
        "FRANCE_TRAVAIL_API_BASE_URL",
        "https://example.com/api/"
    )

    with pytest.raises(
        ValueError,
        match="FRANCE_TRAVAIL_CLIENT_ID"
    ):
        load_config()


def test_load_config_missing_client_secret(monkeypatch):
    """
    Vérifie qu'une erreur est levée lorsque le secret est absent.
    """

    monkeypatch.setenv(
        "FRANCE_TRAVAIL_CLIENT_ID",
        "client-id"
    )

    monkeypatch.delenv(
        "FRANCE_TRAVAIL_CLIENT_SECRET",
        raising=False
    )

    monkeypatch.setenv(
        "FRANCE_TRAVAIL_SCOPE",
        "scope"
    )

    monkeypatch.setenv(
        "FRANCE_TRAVAIL_TOKEN_URL",
        "https://example.com/token"
    )

    monkeypatch.setenv(
        "FRANCE_TRAVAIL_API_BASE_URL",
        "https://example.com/api/"
    )

    with pytest.raises(
        ValueError,
        match="FRANCE_TRAVAIL_CLIENT_SECRET"
    ):
        load_config()


def test_load_config_missing_multiple_values(monkeypatch):
    """
    Vérifie que toutes les variables manquantes sont signalées.
    """

    monkeypatch.delenv(
        "FRANCE_TRAVAIL_CLIENT_ID",
        raising=False
    )

    monkeypatch.delenv(
        "FRANCE_TRAVAIL_CLIENT_SECRET",
        raising=False
    )

    monkeypatch.delenv(
        "FRANCE_TRAVAIL_SCOPE",
        raising=False
    )

    monkeypatch.delenv(
        "FRANCE_TRAVAIL_TOKEN_URL",
        raising=False
    )

    monkeypatch.delenv(
        "FRANCE_TRAVAIL_API_BASE_URL",
        raising=False
    )

    with pytest.raises(
        ValueError
    ) as vException:
        load_config()

    assert "FRANCE_TRAVAIL_CLIENT_ID" in str(
        vException.value
    )

    assert "FRANCE_TRAVAIL_CLIENT_SECRET" in str(
        vException.value
    )

    assert "FRANCE_TRAVAIL_SCOPE" in str(
        vException.value
    )

    assert "FRANCE_TRAVAIL_TOKEN_URL" in str(
        vException.value
    )

    assert "FRANCE_TRAVAIL_API_BASE_URL" in str(
        vException.value
    )