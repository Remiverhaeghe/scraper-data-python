"""Tests du client Adzuna"""

import pytest
import requests

from job.sources.adzuna.client import search_jobs
from job.sources.adzuna.config import AdzunaConfig
from tests.job.sources.fake_http import FakeJsonResponse

SECRET_KEY = "secret-key-123"


def build_config():
    """Construit une configuration de test."""

    rConfig = AdzunaConfig(app_id="test-id", app_key=SECRET_KEY)

    return rConfig


class FakeResponse(FakeJsonResponse):
    """Réponse HTTP simulée."""

    def __init__(self, pStatusCode=200, pData=None):
        self.status_code = pStatusCode
        self.data = pData

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(
                f"{self.status_code} Client Error for url: "
                f"https://api.adzuna.com/?app_key={SECRET_KEY}",
                response=self,
            )

    def json(self):
        if self.data is None:
            raise ValueError("JSON invalide")

        return self.data


def test_search_jobs_sends_credentials_and_params(monkeypatch):
    """Vérifie l'URL, les identifiants et les paramètres envoyés."""

    vCalls = []

    def mock_get(pMethod, pUrl, params, headers, timeout, **pOptions):
        vCalls.append({"url": pUrl, "params": params, "timeout": timeout})

        rResponse = FakeResponse(pData={"results": []})

        return rResponse

    monkeypatch.setattr(requests, "request", mock_get)

    rData = search_jobs(build_config(), {"what": "python"}, 2, 20)

    assert rData == {"results": []}
    assert vCalls[0]["url"] == "https://api.adzuna.com/v1/api/jobs/fr/search/2"
    assert vCalls[0]["params"] == {
        "app_id": "test-id",
        "app_key": SECRET_KEY,
        "results_per_page": 20,
        "what": "python",
    }
    assert vCalls[0]["timeout"] == 10


def test_search_jobs_http_error_hides_key(monkeypatch, caplog):
    """Vérifie qu'une erreur HTTP ne révèle pas la clé."""

    monkeypatch.setattr(requests, "request", lambda *args, **kwargs: FakeResponse(401))

    with pytest.raises(RuntimeError) as vError:
        search_jobs(build_config(), {}, 1)

    assert str(vError.value) == "Erreur HTTP Adzuna 401 sur la page 1"
    assert vError.value.__suppress_context__ is True
    assert SECRET_KEY not in caplog.text


def test_search_jobs_network_error_hides_key(monkeypatch, caplog):
    """Vérifie qu'une erreur réseau ne révèle pas la clé."""

    def mock_get(*args, **kwargs):
        raise requests.ConnectionError(f"Max retries with url: ?app_key={SECRET_KEY}")

    monkeypatch.setattr(requests, "request", mock_get)

    with pytest.raises(RuntimeError) as vError:
        search_jobs(build_config(), {}, 1)

    assert SECRET_KEY not in str(vError.value)
    assert "ConnectionError" in str(vError.value)
    assert vError.value.__suppress_context__ is True
    assert SECRET_KEY not in caplog.text


def test_search_jobs_invalid_json(monkeypatch):
    """Vérifie l'erreur levée pour une réponse non JSON."""

    monkeypatch.setattr(requests, "request", lambda *args, **kwargs: FakeResponse())

    with pytest.raises(ValueError, match="Expecting value"):
        search_jobs(build_config(), {}, 1)
