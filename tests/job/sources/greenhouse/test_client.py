"""Tests du client Greenhouse"""

import requests

from job.sources.greenhouse.client import get_jobs
from tests.job.sources.fake_http import FakeJsonResponse


def test_get_jobs(monkeypatch):
    """Vérifie la récupération des offres Greenhouse."""

    vCalls = []

    def mock_get(pMethod, pUrl, params, timeout, **pOptions):
        vCalls.append({"url": pUrl, "params": params, "timeout": timeout})

        class FakeResponse(FakeJsonResponse):

            def raise_for_status(self):
                pass

            def json(self):
                return {"jobs": [{"id": 123, "title": "Python Developer"}]}

        rResponse = FakeResponse()
        return rResponse

    monkeypatch.setattr(requests, "request", mock_get)

    rData = get_jobs("example-board")

    assert rData == {"jobs": [{"id": 123, "title": "Python Developer"}]}

    assert vCalls[0]["url"] == (
        "https://boards-api.greenhouse.io/v1/boards/" "example-board/jobs"
    )

    assert vCalls[0]["params"] == {"content": "true"}

    assert vCalls[0]["timeout"] == 10


def test_get_jobs_http_error(monkeypatch):
    """Vérifie la propagation d'une erreur HTTP."""

    def mock_get(*args, **kwargs):
        raise requests.RequestException("Erreur HTTP")

    monkeypatch.setattr(requests, "request", mock_get)

    try:
        get_jobs("example-board")
        assert False
    except requests.RequestException:
        assert True
