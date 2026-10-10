"""Tests du client Findwork"""

import pytest
import requests

from job.sources.findwork.client import get_jobs
from job.sources.findwork.config import FindworkConfig


class FakeResponse:
    """Réponse HTTP simulée."""

    def __init__(self, pData=None):
        self.data = pData

    def raise_for_status(self):
        pass

    def json(self):
        if self.data is None:
            raise ValueError("JSON invalide")

        return self.data


def test_get_jobs_sends_token_and_params(monkeypatch):
    """Vérifie l'URL, l'en-tête d'authentification et les paramètres."""

    vCalls = []

    def mock_get(pUrl, params, headers, timeout):
        vCalls.append({"url": pUrl, "params": params, "headers": headers})

        rResponse = FakeResponse({"results": [], "next": None})

        return rResponse

    monkeypatch.setattr(requests, "get", mock_get)

    rData = get_jobs(FindworkConfig("test-key"), {"search": "python"}, 2)

    assert rData == {"results": [], "next": None}
    assert vCalls[0]["url"] == "https://findwork.dev/api/jobs/"
    assert vCalls[0]["params"] == {"search": "python", "page": 2}
    assert vCalls[0]["headers"]["Authorization"] == "Token test-key"


def test_get_jobs_invalid_json(monkeypatch):
    """Vérifie l'erreur levée pour une réponse non JSON."""

    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: FakeResponse())

    with pytest.raises(ValueError, match="JSON valide"):
        get_jobs(FindworkConfig("test-key"), {})
