"""Tests des appels sécurisés aux API des sources"""

import pytest
import requests

from utils.api_client import request_json


class FakeStreamResponse:
    """Réponse HTTP simulée, lue en flux comme par requests avec stream=True."""

    def __init__(
        self,
        pBody=b'{"jobs": []}',
        pStatusCode=200,
        pHeaders=None,
        pIsRedirect=False,
    ):
        self.body = pBody
        self.status_code = pStatusCode
        self.headers = {"Content-Type": "application/json"} | (pHeaders or {})
        self.is_redirect = pIsRedirect
        self.closed = False

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code}", response=self)

    def iter_content(self, chunk_size):
        for vStart in range(0, len(self.body), chunk_size):
            yield self.body[vStart : vStart + chunk_size]

    def close(self):
        self.closed = True


@pytest.fixture
def calls(monkeypatch):
    """Neutralise la résolution DNS et mémorise les appels envoyés."""

    rCalls = []

    monkeypatch.setattr("utils.api_client.validate_url", lambda pUrl: True)

    return rCalls


def use_response(pMonkeypatch, pCalls, pResponse):
    """Fait renvoyer pResponse par requests.request en mémorisant l'appel."""

    def mock_request(pMethod, pUrl, **pOptions):
        pCalls.append({"method": pMethod, "url": pUrl, **pOptions})

        return pResponse

    pMonkeypatch.setattr(requests, "request", mock_request)


def test_request_json_decodes_response(monkeypatch, calls):
    """Vérifie le décodage et les options de sécurité envoyées à requests."""

    vResponse = FakeStreamResponse(b'{"jobs": [{"id": 1}]}')
    use_response(monkeypatch, calls, vResponse)

    rData = request_json("GET", "https://api.example.com/jobs", pParams={"q": "java"})

    assert rData == {"jobs": [{"id": 1}]}
    assert calls[0]["allow_redirects"] is False
    assert calls[0]["stream"] is True
    assert calls[0]["params"] == {"q": "java"}
    assert vResponse.closed


def test_request_json_refuses_redirect(monkeypatch, calls):
    """Vérifie qu'une redirection, vecteur de détournement, est refusée."""

    vResponse = FakeStreamResponse(pStatusCode=302, pIsRedirect=True)
    use_response(monkeypatch, calls, vResponse)

    with pytest.raises(ValueError, match="Redirection refusée"):
        request_json("GET", "https://api.example.com/jobs")

    assert vResponse.closed


def test_request_json_refuses_announced_oversize(monkeypatch, calls):
    """Vérifie le refus d'une réponse dont la taille annoncée est excessive."""

    use_response(
        monkeypatch, calls, FakeStreamResponse(pHeaders={"Content-Length": "2048"})
    )

    with pytest.raises(ValueError, match="taille"):
        request_json("GET", "https://api.example.com/jobs", pMaxSize=1024)


def test_request_json_refuses_real_oversize(monkeypatch, calls):
    """Vérifie le refus d'une réponse qui dépasse la limite sans l'annoncer."""

    vBody = b'{"data": "' + b"x" * 5000 + b'"}'
    use_response(monkeypatch, calls, FakeStreamResponse(vBody))

    with pytest.raises(ValueError, match="taille"):
        request_json("GET", "https://api.example.com/jobs", pMaxSize=1024)


def test_request_json_refuses_non_json_content(monkeypatch, calls):
    """Vérifie le refus d'un contenu qui n'est pas du JSON, comme une page HTML."""

    use_response(
        monkeypatch,
        calls,
        FakeStreamResponse(b"<html></html>", pHeaders={"Content-Type": "text/html"}),
    )

    with pytest.raises(ValueError, match="text/html"):
        request_json("GET", "https://api.example.com/jobs")


def test_request_json_propagates_http_error(monkeypatch, calls):
    """Vérifie que l'erreur HTTP garde la réponse, pour lire son code."""

    use_response(monkeypatch, calls, FakeStreamResponse(pStatusCode=503))

    with pytest.raises(requests.HTTPError) as vError:
        request_json("GET", "https://api.example.com/jobs")

    assert vError.value.response.status_code == 503


def test_request_json_validates_destination(monkeypatch):
    """Vérifie qu'une destination interne est refusée avant tout appel."""

    def fail_request(*pArgs, **pKwargs):
        raise AssertionError("Aucun appel ne doit partir vers une adresse interne")

    monkeypatch.setattr(requests, "request", fail_request)

    with pytest.raises(ValueError, match="destination"):
        request_json("GET", "http://127.0.0.1:8000/admin")
