"""Tests du client Himalayas"""

import pytest
import requests

from job.sources.himalayas.client import search_jobs


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


def test_search_jobs_sends_filters(monkeypatch):
    """Vérifie l'URL et les paramètres envoyés."""

    vCalls = []

    def mock_get(pUrl, params, headers, timeout):
        vCalls.append({"url": pUrl, "params": params, "timeout": timeout})

        rResponse = FakeResponse({"jobs": [], "totalCount": 0})

        return rResponse

    monkeypatch.setattr(requests, "get", mock_get)

    rData = search_jobs("python", "France", 2)

    assert rData == {"jobs": [], "totalCount": 0}
    assert vCalls[0]["url"] == "https://himalayas.app/jobs/api/search"
    assert vCalls[0]["params"] == {"page": 2, "q": "python", "country": "France"}
    assert vCalls[0]["timeout"] == 10


def test_search_jobs_invalid_json(monkeypatch):
    """Vérifie l'erreur levée pour une réponse non JSON."""

    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: FakeResponse())

    with pytest.raises(ValueError, match="JSON valide"):
        search_jobs()
