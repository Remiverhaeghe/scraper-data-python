"""Tests du client Jooble"""

import pytest
import requests

from job.sources.jooble.client import search_jobs
from job.sources.jooble.config import JoobleConfig
from tests.job.sources.fake_http import FakeJsonResponse

SECRET_KEY = "secret-key-123"


class FakeResponse(FakeJsonResponse):
    """Réponse HTTP simulée."""

    def __init__(self, pStatusCode=200, pData=None):
        self.status_code = pStatusCode
        self.data = pData

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(
                f"{self.status_code} Client Error for url: "
                f"https://jooble.org/api/{SECRET_KEY}",
                response=self,
            )

    def json(self):
        if self.data is None:
            raise ValueError("JSON invalide")

        return self.data


def test_search_jobs_posts_body(monkeypatch):
    """Vérifie l'URL et le corps de la requête."""

    vCalls = []

    def mock_post(pMethod, pUrl, json, timeout, **pOptions):
        vCalls.append({"url": pUrl, "json": json, "timeout": timeout})

        rResponse = FakeResponse(pData={"totalCount": 0, "jobs": []})

        return rResponse

    monkeypatch.setattr(requests, "request", mock_post)

    rData = search_jobs(JoobleConfig(SECRET_KEY), {"keywords": "python"})

    assert rData == {"totalCount": 0, "jobs": []}
    assert vCalls[0]["url"] == f"https://jooble.org/api/{SECRET_KEY}"
    assert vCalls[0]["json"] == {"keywords": "python"}
    assert vCalls[0]["timeout"] == 10


def test_search_jobs_http_error_hides_key(monkeypatch, caplog):
    """Vérifie qu'une erreur HTTP ne révèle pas la clé."""

    monkeypatch.setattr(requests, "request", lambda *args, **kwargs: FakeResponse(403))

    with pytest.raises(RuntimeError) as vError:
        search_jobs(JoobleConfig(SECRET_KEY), {})

    assert str(vError.value) == "Erreur HTTP Jooble 403"
    assert vError.value.__suppress_context__ is True
    assert SECRET_KEY not in caplog.text


def test_search_jobs_network_error_hides_key(monkeypatch, caplog):
    """Vérifie qu'une erreur réseau ne révèle pas la clé."""

    def mock_post(*args, **kwargs):
        raise requests.ConnectionError(f"Max retries with url: /api/{SECRET_KEY}")

    monkeypatch.setattr(requests, "request", mock_post)

    with pytest.raises(RuntimeError) as vError:
        search_jobs(JoobleConfig(SECRET_KEY), {})

    assert SECRET_KEY not in str(vError.value)
    assert vError.value.__suppress_context__ is True
    assert SECRET_KEY not in caplog.text
