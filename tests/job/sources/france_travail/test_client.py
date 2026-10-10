"""Tests du client France Travail"""

import requests

from job.sources.france_travail.client import search_jobs
from tests.job.sources.fake_http import FakeJsonResponse


class FakeConfig:
    """Configuration fictive utilisée par les tests."""

    api_base_url = "https://example.com/"


def test_search_jobs(monkeypatch):
    """Vérifie l'appel de recherche des offres."""

    vCalls = []

    def mock_get(pMethod, pUrl, headers, params, timeout, **pOptions):
        vCalls.append(
            {"url": pUrl, "headers": headers, "params": params, "timeout": timeout}
        )

        class FakeResponse(FakeJsonResponse):

            def raise_for_status(self):
                pass

            def json(self):
                return {"resultats": [{"id": "123"}]}

        rResponse = FakeResponse()
        return rResponse

    def mock_get_access_token(pConfig):
        return "token-test"

    monkeypatch.setattr(requests, "request", mock_get)

    monkeypatch.setattr(
        "job.sources.france_travail.client.get_access_token", mock_get_access_token
    )

    vParams = {"motsCles": "python", "commune": "59000"}

    rData = search_jobs(FakeConfig(), vParams)

    assert rData == {"resultats": [{"id": "123"}]}

    assert vCalls[0]["url"] == ("https://example.com/" "offresdemploi/v2/offres/search")

    assert vCalls[0]["headers"] == {
        "Authorization": "Bearer token-test",
        "Accept": "application/json",
    }

    assert vCalls[0]["params"] == vParams
    assert vCalls[0]["timeout"] == 10


def test_search_jobs_http_error(monkeypatch):
    """Vérifie la propagation d'une erreur HTTP."""

    def mock_get_access_token(pConfig):
        return "token-test"

    def mock_get(*args, **kwargs):
        raise requests.RequestException("Erreur HTTP")

    monkeypatch.setattr(
        "job.sources.france_travail.client.get_access_token", mock_get_access_token
    )

    monkeypatch.setattr(requests, "request", mock_get)

    try:
        search_jobs(FakeConfig(), {})
        assert False
    except requests.RequestException:
        assert True


def test_search_jobs_adds_range_parameter(monkeypatch):
    """Vérifie que la plage de résultats est transmise à l'API."""

    vCalls = []

    def mock_get(pMethod, pUrl, headers, params, timeout, **pOptions):
        vCalls.append(params)

        class FakeResponse(FakeJsonResponse):

            def raise_for_status(self):
                pass

            def json(self):
                return {"resultats": []}

        rResponse = FakeResponse()
        return rResponse

    def mock_get_access_token(pConfig):
        return "token-test"

    monkeypatch.setattr(requests, "request", mock_get)

    monkeypatch.setattr(
        "job.sources.france_travail.client.get_access_token", mock_get_access_token
    )

    search_jobs(FakeConfig(), {"motsCles": "python"}, pRange="150-299")

    assert vCalls == [{"motsCles": "python", "range": "150-299"}]
