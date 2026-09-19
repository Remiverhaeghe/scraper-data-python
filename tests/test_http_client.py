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

    mock_get.return_value = vResponse

    rHtml = fetch_page(
        "https://example.com",
        pTimeout=30
    )

    mock_get.assert_called_once_with(
        "https://example.com",
        timeout=30
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