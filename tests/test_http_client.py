"""
Tests du client HTTP.
"""

from unittest.mock import patch

import pytest
import requests

from scraper.http_client import fetch_page


def test_fetch_page_with_invalid_url():
    """Vérifie la gestion d'une erreur HTTP."""

    url = "https://example.com/page-inexistante"

    with pytest.raises(requests.HTTPError):
        fetch_page(url)


def test_fetch_page_with_utf8_encoding():
    """Vérifie que l'encodage détecté est utilisé."""

    response = requests.Response()
    response.status_code = 200
    response._content = "Prix : £51.77".encode("utf-8")

    with patch(
        "scraper.http_client.requests.get",
        return_value=response
    ):
        with patch.object(
            type(response),
            "apparent_encoding",
            new_callable=lambda: property(
                lambda self: "utf-8"
            )
        ):
            result = fetch_page("https://example.com")

    assert response.encoding == "utf-8"
    assert result == "Prix : £51.77"

def test_fetch_page_http_error(monkeypatch):
    """Vérifie qu'une erreur HTTP est bien remontée."""

    class FakeResponse:
        def raise_for_status(self):
            raise requests.HTTPError("404 Not Found")

    def fake_get(url, timeout):
        return FakeResponse()

    monkeypatch.setattr(requests, "get", fake_get)

    with pytest.raises(requests.HTTPError):
        fetch_page("https://example.com/page")


def test_fetch_page_timeout(monkeypatch):
    """Vérifie qu'un timeout HTTP est bien remonté."""

    def fake_get(url, timeout):
        raise requests.Timeout("Request timed out")

    monkeypatch.setattr(requests, "get", fake_get)

    with pytest.raises(requests.Timeout):
        fetch_page("https://example.com/page")