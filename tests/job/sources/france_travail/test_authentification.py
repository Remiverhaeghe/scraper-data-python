# ============================================================================
# Tests de l'authentification France Travail
# ============================================================================

import requests
import pytest

from job.sources.france_travail.authentication import (
    get_access_token
)


class FakeConfig:
    """
    Configuration fictive utilisée par les tests.
    """

    client_id = "test-client"
    client_secret = "test-secret"
    token_url = "https://example.com/token"
    scope = "test-scope"


def test_get_access_token(monkeypatch):
    """
    Vérifie la récupération du jeton OAuth2.
    """

    class FakeResponse:

        def raise_for_status(self):
            pass

        def json(self):
            return {
                "access_token": "token-test"
            }

    def mock_post(pUrl, data, timeout):
        assert pUrl == FakeConfig.token_url
        assert data["grant_type"] == "client_credentials"
        assert data["client_id"] == "test-client"
        assert data["client_secret"] == "test-secret"
        assert data["scope"] == "test-scope"
        assert timeout == 10

        rResponse = FakeResponse()
        return rResponse

    monkeypatch.setattr(
        requests,
        "post",
        mock_post
    )

    rToken = get_access_token(
        FakeConfig()
    )

    assert rToken == "token-test"


def test_get_access_token_without_token(monkeypatch):
    """
    Vérifie l'erreur lorsqu'aucun jeton n'est retourné.
    """

    class FakeResponse:

        def raise_for_status(self):
            pass

        def json(self):
            return {}

    def mock_post(*args, **kwargs):
        rResponse = FakeResponse()
        return rResponse

    monkeypatch.setattr(
        requests,
        "post",
        mock_post
    )

    with pytest.raises(
        ValueError,
        match="jeton d'accès"
    ):
        get_access_token(
            FakeConfig()
        )


def test_get_access_token_http_error(monkeypatch):
    """
    Vérifie la propagation d'une erreur HTTP.
    """

    def mock_post(*args, **kwargs):
        raise requests.RequestException(
            "Erreur HTTP"
        )

    monkeypatch.setattr(
        requests,
        "post",
        mock_post
    )

    with pytest.raises(
        requests.RequestException
    ):
        get_access_token(
            FakeConfig()
        )