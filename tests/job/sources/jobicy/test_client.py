"""Tests du client Jobicy"""

import pytest
import requests

from job.sources.jobicy.client import get_jobs
from tests.job.sources.fake_http import FakeJsonResponse


class FakeResponse(FakeJsonResponse):
    """Réponse HTTP simulée."""

    def __init__(self, pData=None):
        self.data = pData

    def raise_for_status(self):
        pass

    def json(self):
        if self.data is None:
            raise ValueError("JSON invalide")

        return self.data


def test_get_jobs_sends_filters(monkeypatch):
    """Vérifie l'URL et les paramètres envoyés."""

    vCalls = []

    def mock_get(pMethod, pUrl, params, headers, timeout, **pOptions):
        vCalls.append({"url": pUrl, "params": params, "timeout": timeout})

        rResponse = FakeResponse({"jobs": [{"id": 1}]})

        return rResponse

    monkeypatch.setattr(requests, "request", mock_get)

    rJobs = get_jobs("python", "france", 50)

    assert rJobs == [{"id": 1}]
    assert vCalls[0]["url"] == "https://jobicy.com/api/v2/remote-jobs"
    assert vCalls[0]["params"] == {"count": 50, "geo": "france", "tag": "python"}
    assert vCalls[0]["timeout"] == 10


def test_get_jobs_invalid_json(monkeypatch):
    """Vérifie l'erreur levée pour une réponse non JSON."""

    monkeypatch.setattr(requests, "request", lambda *args, **kwargs: FakeResponse())

    with pytest.raises(ValueError, match="Expecting value"):
        get_jobs()
