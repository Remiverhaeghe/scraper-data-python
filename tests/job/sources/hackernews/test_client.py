"""Tests du client Hacker News"""

import pytest
import requests

from job.sources.hackernews import client
from job.sources.hackernews.client import find_latest_thread_id, get_json, get_thread
from tests.job.sources.fake_http import FakeJsonResponse


def test_find_latest_thread_id_skips_other_threads(monkeypatch):
    """Vérifie que seul le fil « Who is hiring? » est retenu."""

    vCalls = []

    def mock_get_json(pUrl, pParams=None):
        vCalls.append({"url": pUrl, "params": pParams})

        rData = {
            "hits": [
                {"objectID": "2", "title": "Ask HN: Who wants to be hired? (Oct)"},
                {"objectID": "1", "title": "Ask HN: Who is hiring? (Oct)"},
            ]
        }

        return rData

    monkeypatch.setattr(client, "get_json", mock_get_json)

    assert find_latest_thread_id() == "1"
    assert vCalls[0]["params"]["tags"] == "story,author_whoishiring"


def test_find_latest_thread_id_without_thread(monkeypatch):
    """Vérifie l'erreur levée lorsqu'aucun fil n'est trouvé."""

    monkeypatch.setattr(client, "get_json", lambda pUrl, pParams=None: {"hits": []})

    with pytest.raises(ValueError, match="Who is hiring"):
        find_latest_thread_id()


def test_get_thread_requests_item(monkeypatch):
    """Vérifie l'URL utilisée pour récupérer un fil."""

    vCalls = []

    def mock_get_json(pUrl, pParams=None):
        vCalls.append(pUrl)

        rData = {"children": []}

        return rData

    monkeypatch.setattr(client, "get_json", mock_get_json)

    assert get_thread("49922569") == {"children": []}
    assert vCalls == ["https://hn.algolia.com/api/v1/items/49922569"]


def test_get_json_propagates_http_error(monkeypatch):
    """Vérifie qu'une erreur HTTP d'Algolia est propagée."""

    def mock_request(pMethod, pUrl, **pOptions):
        raise requests.ConnectionError("Algolia injoignable")

    monkeypatch.setattr(requests, "request", mock_request)

    with pytest.raises(requests.ConnectionError):
        get_json("https://hn.algolia.com/api/v1/search")


def test_get_json_reports_invalid_content(monkeypatch):
    """Vérifie qu'un contenu refusé par le client sécurisé est signalé."""

    def mock_request(pMethod, pUrl, **pOptions):
        rResponse = FakeJsonResponse()
        rResponse.headers = {"Content-Type": "text/html"}

        return rResponse

    monkeypatch.setattr(requests, "request", mock_request)

    with pytest.raises(ValueError, match="Hacker News : Réponse inattendue"):
        get_json("https://hn.algolia.com/api/v1/search")
