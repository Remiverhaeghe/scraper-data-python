"""Tests du client HTTP de l'API publique Lever"""

import pytest
import requests

from job.sources.lever.client import get_jobs
from tests.job.sources.fake_http import FakeJsonResponse


class FakeResponse(FakeJsonResponse):
    """Réponse HTTP simulée."""

    def __init__(self, pData=None, pError=None):
        self.data = pData
        self.error = pError

    def raise_for_status(self):
        if self.error is not None:
            raise self.error

    def json(self):
        if self.data is None:
            raise ValueError("JSON invalide")

        return self.data


def test_get_jobs(monkeypatch):
    """Vérifie la récupération des offres Lever."""

    def mock_request(pMethod, pUrl, params, headers, timeout, **pOptions):
        assert pMethod == "GET"
        assert pUrl == "https://api.lever.co/v0/postings/example-company"

        assert params["mode"] == "json"
        assert params["limit"] == 50
        assert params["skip"] == 100

        assert headers["Accept"] == "application/json"
        assert timeout == 10
        assert pOptions["allow_redirects"] is False

        return FakeResponse([{"id": "job-1", "text": "Python Developer"}])

    monkeypatch.setattr(requests, "request", mock_request)

    rData = get_jobs("example-company", pLimit=50, pSkip=100)

    assert len(rData) == 1
    assert rData[0]["id"] == "job-1"


def test_get_jobs_without_offset(monkeypatch):
    """Vérifie que le scraping commence à l'offset zéro."""

    def mock_request(pMethod, pUrl, params, headers, timeout, **pOptions):
        assert params["limit"] == 100
        assert params["skip"] == 0

        return FakeResponse([{"id": "job-1"}])

    monkeypatch.setattr(requests, "request", mock_request)

    rData = get_jobs("example-company")

    assert len(rData) == 1


def test_get_jobs_http_error(monkeypatch):
    """Vérifie qu'une erreur HTTP est propagée."""

    monkeypatch.setattr(
        requests,
        "request",
        lambda *args, **kwargs: FakeResponse(
            pError=requests.HTTPError("Erreur HTTP 503")
        ),
    )

    with pytest.raises(requests.HTTPError, match="503"):
        get_jobs("example-company")


def test_get_jobs_invalid_json(monkeypatch):
    """Vérifie qu'une réponse non JSON provoque une erreur explicite."""

    monkeypatch.setattr(requests, "request", lambda *args, **kwargs: FakeResponse())

    with pytest.raises(ValueError, match="Lever : Expecting value"):
        get_jobs("example-company")
