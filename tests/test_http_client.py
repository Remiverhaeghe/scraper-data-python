# ============================================================================
# Tests du client HTTP du scraper
# ============================================================================


from unittest.mock import Mock, patch

import pytest
import requests

from scraper.http_client import fetch_page


@patch("scraper.http_client.requests.get")
def test_fetch_page(mock_get):
    """
    Vérifie que le contenu HTML d'une page est correctement récupéré.
    """

    vResponse = Mock()
    vResponse.text = "<html>Test</html>"
    vResponse.apparent_encoding = "utf-8"
    vResponse.status_code = 200
    vResponse.is_redirect = False

    mock_get.return_value = vResponse

    rHtml = fetch_page(
        "https://example.com",
        pTimeout=30
    )

    mock_get.assert_called_once_with(
        "https://example.com",
        timeout=30,
        allow_redirects=False
    )

    vResponse.raise_for_status.assert_called_once()

    assert rHtml == "<html>Test</html>"


@patch("scraper.http_client.requests.get")
def test_fetch_page_with_default_encoding(mock_get):
    """
    Vérifie que l'encodage détecté est appliqué à la réponse.
    """

    vResponse = Mock()
    vResponse.text = "Contenu français"
    vResponse.apparent_encoding = "utf-8"
    vResponse.status_code = 200
    vResponse.is_redirect = False

    mock_get.return_value = vResponse

    rHtml = fetch_page(
        "https://example.com",
        pTimeout=10
    )

    assert vResponse.encoding == "utf-8"
    assert rHtml == "Contenu français"


@patch("scraper.http_client.requests.get")
def test_fetch_page_with_http_error(mock_get):
    """
    Vérifie qu'une erreur HTTP est propagée.
    """

    vResponse = Mock()
    vResponse.status_code = 404
    vResponse.is_redirect = False

    vResponse.raise_for_status.side_effect = requests.HTTPError(
        "404 Not Found"
    )

    mock_get.return_value = vResponse

    with pytest.raises(requests.HTTPError):
        fetch_page(
            "https://example.com/page-inexistante",
            pTimeout=10
        )


@patch("scraper.http_client.requests.get")
def test_fetch_page_with_request_error(mock_get):
    """
    Vérifie qu'une erreur Requests est propagée.
    """

    mock_get.side_effect = requests.RequestException(
        "Erreur de connexion"
    )

    with pytest.raises(requests.RequestException):
        fetch_page(
            "https://example.com",
            pTimeout=10
        )

def test_fetch_page_rejects_unsafe_url():
    """
    Vérifie qu'une URL interdite est rejetée avant la requête HTTP.
    """

    with patch(
        "scraper.http_client.validate_url",
        side_effect=ValueError("URL interdite")
    ), patch(
        "scraper.http_client.requests.get"
    ) as vMockGet:
        with pytest.raises(ValueError):
            fetch_page("http://127.0.0.1", 10)

    vMockGet.assert_not_called()

def test_fetch_page_rejects_unsafe_redirect():
    """
    Vérifie qu'une redirection vers une destination interdite est refusée.
    """

    vResponse = Mock()
    vResponse.status_code = 302
    vResponse.is_redirect = True
    vResponse.headers = {
        "Location": "http://127.0.0.1:8080"
    }

    with patch(
        "scraper.http_client.validate_url"
    ) as vMockValidate, patch(
        "scraper.http_client.requests.get",
        return_value=vResponse
    ):
        vMockValidate.side_effect = [
            None,
            ValueError("URL interdite")
        ]

        with pytest.raises(ValueError):
            fetch_page("https://example.com", 10)

def test_fetch_page_allows_safe_redirect():
    """
    Vérifie qu'une redirection vers une URL autorisée est suivie.
    """

    vFirstResponse = Mock()
    vFirstResponse.status_code = 302
    vFirstResponse.is_redirect = True
    vFirstResponse.headers = {
        "Location": "https://example.com/page-2"
    }

    vSecondResponse = Mock()
    vSecondResponse.status_code = 200
    vSecondResponse.is_redirect = False
    vSecondResponse.text = "<html>Page 2</html>"
    vSecondResponse.apparent_encoding = "utf-8"

    with patch(
        "scraper.http_client.requests.get",
        side_effect=[
            vFirstResponse,
            vSecondResponse
        ]
    ):
        rHtml = fetch_page(
            "https://example.com",
            pTimeout=10
        )

    assert rHtml == "<html>Page 2</html>"


def test_fetch_page_rejects_too_many_redirects():
    """
    Vérifie que le nombre maximum de redirections est respecté.
    """

    vResponse = Mock()
    vResponse.status_code = 302
    vResponse.is_redirect = True
    vResponse.headers = {
        "Location": "https://example.com"
    }

    with patch(
        "scraper.http_client.requests.get",
        return_value=vResponse
    ):
        with pytest.raises(ValueError):
            fetch_page(
                "https://example.com",
                pTimeout=10
            )

def test_fetch_page_rejects_redirect_without_location():
    """
    Vérifie qu'une redirection sans destination est refusée.
    """

    vResponse = Mock()
    vResponse.status_code = 302
    vResponse.is_redirect = True
    vResponse.headers = {}

    with patch(
        "scraper.http_client.requests.get",
        return_value=vResponse
    ):
        with pytest.raises(ValueError):
            fetch_page(
                "https://example.com",
                pTimeout=10
            )