"""Tests du client Arbeitnow"""

import pytest
import requests

from job.sources.arbeitnow.client import get_jobs


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


def test_get_jobs_requests_page(monkeypatch):
    """Vérifie l'URL et la page demandée."""

    vCalls = []

    def mock_get(pUrl, params, headers, timeout):
        vCalls.append({"url": pUrl, "params": params, "timeout": timeout})

        rResponse = FakeResponse({"data": [], "links": {}})

        return rResponse

    monkeypatch.setattr(requests, "get", mock_get)

    rData = get_jobs(2)

    assert rData == {"data": [], "links": {}}
    assert vCalls[0]["url"] == "https://www.arbeitnow.com/api/job-board-api"
    assert vCalls[0]["params"] == {"page": 2}
    assert vCalls[0]["timeout"] == 10


def test_get_jobs_invalid_json(monkeypatch):
    """Vérifie l'erreur levée pour une réponse non JSON."""

    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: FakeResponse())

    with pytest.raises(ValueError, match="JSON valide"):
        get_jobs()
