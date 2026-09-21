# ============================================================================
# Tests du client HTTP du scraper
# ============================================================================


from unittest.mock import Mock, patch

import pytest
import requests

from scraper.config import ScrapingConfig
from scraper.http_client import fetch_page


@patch("scraper.http_client.requests.get")
def test_fetch_page(mock_get):
    """
    Vérifie que le contenu HTML d'une page est correctement récupéré.
    """

    vResponse = Mock()
    vResponse.apparent_encoding = "utf-8"
    vResponse.status_code = 200
    vResponse.is_redirect = False
    vResponse.headers = {}
    vResponse.iter_content.return_value = [
        b"<html>Test</html>"
    ]

    mock_get.return_value = vResponse

    vConfig = ScrapingConfig(timeout=30)

    rHtml = fetch_page(
        "https://example.com",
        vConfig
    )

    mock_get.assert_called_once_with(
        "https://example.com",
        timeout=30,
        allow_redirects=False,
        stream=True
    )

    vResponse.raise_for_status.assert_called_once()

    assert rHtml == "<html>Test</html>"


@patch("scraper.http_client.requests.get")
def test_fetch_page_with_default_encoding(mock_get):
    """
    Vérifie que l'encodage détecté est appliqué à la réponse.
    """

    vResponse = Mock()
    vResponse.apparent_encoding = "utf-8"
    vResponse.status_code = 200
    vResponse.is_redirect = False
    vResponse.headers = {}
    vResponse.iter_content.return_value = [
        "Contenu français".encode("utf-8")
    ]

    mock_get.return_value = vResponse

    vConfig = ScrapingConfig()

    rHtml = fetch_page(
        "https://example.com",
        vConfig
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
    vResponse.headers = {}

    vResponse.raise_for_status.side_effect = requests.HTTPError(
        "404 Not Found"
    )

    mock_get.return_value = vResponse

    vConfig = ScrapingConfig()

    with pytest.raises(requests.HTTPError):
        fetch_page(
            "https://example.com/page-inexistante",
            vConfig
        )


@patch("scraper.http_client.requests.get")
def test_fetch_page_with_request_error(mock_get):
    """
    Vérifie qu'une erreur Requests est propagée.
    """

    mock_get.side_effect = requests.RequestException(
        "Erreur de connexion"
    )

    vConfig = ScrapingConfig()

    with pytest.raises(requests.RequestException):
        fetch_page(
            "https://example.com",
            vConfig
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
        vConfig = ScrapingConfig()

        with pytest.raises(ValueError):
            fetch_page(
                "http://127.0.0.1",
                vConfig
            )

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

        vConfig = ScrapingConfig()

        with pytest.raises(ValueError):
            fetch_page(
                "https://example.com",
                vConfig
            )


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
    vSecondResponse.apparent_encoding = "utf-8"
    vSecondResponse.headers = {}
    vSecondResponse.iter_content.return_value = [
        b"<html>Page 2</html>"
    ]

    with patch(
        "scraper.http_client.requests.get",
        side_effect=[
            vFirstResponse,
            vSecondResponse
        ]
    ):
        vConfig = ScrapingConfig()

        rHtml = fetch_page(
            "https://example.com",
            vConfig
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
        vConfig = ScrapingConfig()

        with pytest.raises(ValueError):
            fetch_page(
                "https://example.com",
                vConfig
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
        vConfig = ScrapingConfig()

        with pytest.raises(ValueError):
            fetch_page(
                "https://example.com",
                vConfig
            )


def test_fetch_page_accepts_response_under_size_limit():
    """
    Vérifie qu'une réponse inférieure à la limite est acceptée.
    """

    vResponse = Mock()
    vResponse.status_code = 200
    vResponse.is_redirect = False
    vResponse.headers = {
        "Content-Length": str(4 * 1024 * 1024)
    }
    vResponse.apparent_encoding = "utf-8"
    vResponse.iter_content.return_value = [
        b"<html>Test</html>"
    ]

    with patch(
        "scraper.http_client.requests.get",
        return_value=vResponse
    ):
        vConfig = ScrapingConfig(
            max_response_size_mb=5
        )

        rHtml = fetch_page(
            "https://example.com",
            vConfig
        )

    assert rHtml == "<html>Test</html>"


def test_fetch_page_accepts_response_at_size_limit():
    """
    Vérifie qu'une réponse égale à la limite est acceptée.
    """

    vResponse = Mock()
    vResponse.status_code = 200
    vResponse.is_redirect = False
    vResponse.headers = {
        "Content-Length": str(5 * 1024 * 1024)
    }
    vResponse.apparent_encoding = "utf-8"
    vResponse.iter_content.return_value = [
        b"<html>Test</html>"
    ]

    with patch(
        "scraper.http_client.requests.get",
        return_value=vResponse
    ):
        vConfig = ScrapingConfig(
            max_response_size_mb=5
        )

        rHtml = fetch_page(
            "https://example.com",
            vConfig
        )

    assert rHtml == "<html>Test</html>"


def test_fetch_page_rejects_response_over_size_limit():
    """
    Vérifie qu'une réponse supérieure à la limite est refusée.
    """

    vResponse = Mock()
    vResponse.status_code = 200
    vResponse.is_redirect = False
    vResponse.headers = {
        "Content-Length": str(6 * 1024 * 1024)
    }

    with patch(
        "scraper.http_client.requests.get",
        return_value=vResponse
    ):
        vConfig = ScrapingConfig(
            max_response_size_mb=5
        )

        with pytest.raises(ValueError):
            fetch_page(
                "https://example.com",
                vConfig
            )

def test_fetch_page_accepts_chunked_response_under_size_limit():
    """
    Vérifie qu'une réponse sans Content-Length respectant la limite est acceptée.
    """

    vResponse = Mock()
    vResponse.status_code = 200
    vResponse.is_redirect = False
    vResponse.headers = {}
    vResponse.apparent_encoding = "utf-8"
    vResponse.iter_content.return_value = [
        b"Premier morceau",
        b"Deuxieme morceau"
    ]

    with patch(
        "scraper.http_client.requests.get",
        return_value=vResponse
    ):
        vConfig = ScrapingConfig(
            max_response_size_mb=5
        )

        rHtml = fetch_page(
            "https://example.com",
            vConfig
        )

    assert rHtml == "Premier morceauDeuxieme morceau"


def test_fetch_page_rejects_chunked_response_over_size_limit():
    """
    Vérifie qu'une réponse sans Content-Length dépassant la limite est refusée.
    """

    vResponse = Mock()
    vResponse.status_code = 200
    vResponse.is_redirect = False
    vResponse.headers = {}
    vResponse.apparent_encoding = "utf-8"
    vResponse.iter_content.return_value = [
        b"a" * (4 * 1024 * 1024),
        b"b" * (2 * 1024 * 1024)
    ]

    with patch(
        "scraper.http_client.requests.get",
        return_value=vResponse
    ):
        vConfig = ScrapingConfig(
            max_response_size_mb=5
        )

        with pytest.raises(ValueError):
            fetch_page(
                "https://example.com",
                vConfig
            )

@patch("scraper.http_client.requests.get")
def test_fetch_page_retries_after_request_error(mock_get):
    """
    Vérifie qu'une nouvelle tentative est effectuée après une erreur réseau.
    """

    vResponse = Mock()
    vResponse.status_code = 200
    vResponse.is_redirect = False
    vResponse.headers = {}
    vResponse.apparent_encoding = "utf-8"
    vResponse.iter_content.return_value = [
        b"<html>Test</html>"
    ]

    mock_get.side_effect = [
        requests.RequestException("Erreur de connexion"),
        vResponse
    ]

    vConfig = ScrapingConfig(
        retry_count=1,
        retry_delay=0
    )

    rHtml = fetch_page(
        "https://example.com",
        vConfig
    )

    assert rHtml == "<html>Test</html>"
    assert mock_get.call_count == 2


@patch("scraper.http_client.requests.get")
def test_fetch_page_stops_after_max_retries(mock_get):
    """
    Vérifie que le nombre maximum de tentatives est respecté.
    """

    mock_get.side_effect = requests.RequestException(
        "Erreur de connexion"
    )

    vConfig = ScrapingConfig(
        retry_count=2,
        retry_delay=0
    )

    with pytest.raises(requests.RequestException):
        fetch_page(
            "https://example.com",
            vConfig
        )

    assert mock_get.call_count == 3


@patch("scraper.http_client.requests.get")
def test_fetch_page_without_retry_only_attempts_once(mock_get):
    """
    Vérifie qu'aucune nouvelle tentative n'est effectuée lorsque
    le retry est désactivé.
    """

    mock_get.side_effect = requests.RequestException(
        "Erreur de connexion"
    )

    vConfig = ScrapingConfig(
        retry_count=0
    )

    with pytest.raises(requests.RequestException):
        fetch_page(
            "https://example.com",
            vConfig
        )

    assert mock_get.call_count == 1


@patch("scraper.http_client.time.sleep")
@patch("scraper.http_client.requests.get")
def test_fetch_page_waits_before_retry(mock_get, mock_sleep):
    """
    Vérifie que le délai configuré est appliqué avant une nouvelle tentative.
    """

    vResponse = Mock()
    vResponse.status_code = 200
    vResponse.is_redirect = False
    vResponse.headers = {}
    vResponse.apparent_encoding = "utf-8"
    vResponse.iter_content.return_value = [
        b"<html>Test</html>"
    ]

    mock_get.side_effect = [
        requests.RequestException("Erreur de connexion"),
        vResponse
    ]

    vConfig = ScrapingConfig(
        retry_count=1,
        retry_delay=2
    )

    rHtml = fetch_page(
        "https://example.com",
        vConfig
    )

    assert rHtml == "<html>Test</html>"
    mock_sleep.assert_called_once_with(2)
    assert mock_get.call_count == 2

@patch("scraper.http_client.time.sleep")
@patch("scraper.http_client.requests.get")
def test_fetch_page_applies_delay_between_requests(
    mock_get,
    mock_sleep
):
    """
    Vérifie que le délai est appliqué entre deux requêtes HTTP.
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
    vSecondResponse.headers = {}
    vSecondResponse.apparent_encoding = "utf-8"
    vSecondResponse.iter_content.return_value = [
        b"<html>Page 2</html>"
    ]

    mock_get.side_effect = [
        vFirstResponse,
        vSecondResponse
    ]

    vConfig = ScrapingConfig(
        delay=2
    )

    rHtml = fetch_page(
        "https://example.com",
        vConfig
    )

    assert rHtml == "<html>Page 2</html>"
    mock_sleep.assert_called_once_with(2)
    assert mock_get.call_count == 2


@patch("scraper.http_client.time.sleep")
@patch("scraper.http_client.requests.get")
def test_fetch_page_applies_delay_between_multiple_redirects(
    mock_get,
    mock_sleep
):
    """
    Vérifie que le délai est appliqué entre plusieurs requêtes.
    """

    vFirstResponse = Mock()
    vFirstResponse.status_code = 302
    vFirstResponse.is_redirect = True
    vFirstResponse.headers = {
        "Location": "https://example.com/page-2"
    }

    vSecondResponse = Mock()
    vSecondResponse.status_code = 302
    vSecondResponse.is_redirect = True
    vSecondResponse.headers = {
        "Location": "https://example.com/page-3"
    }

    vThirdResponse = Mock()
    vThirdResponse.status_code = 200
    vThirdResponse.is_redirect = False
    vThirdResponse.headers = {}
    vThirdResponse.apparent_encoding = "utf-8"
    vThirdResponse.iter_content.return_value = [
        b"<html>Page 3</html>"
    ]

    mock_get.side_effect = [
        vFirstResponse,
        vSecondResponse,
        vThirdResponse
    ]

    vConfig = ScrapingConfig(
        delay=2
    )

    rHtml = fetch_page(
        "https://example.com",
        vConfig
    )

    assert rHtml == "<html>Page 3</html>"
    assert mock_sleep.call_count == 2
    mock_sleep.assert_any_call(2)
    assert mock_get.call_count == 3


@patch("scraper.http_client.time.sleep")
@patch("scraper.http_client.requests.get")
def test_fetch_page_without_delay_does_not_sleep(
    mock_get,
    mock_sleep
):
    """
    Vérifie qu'aucun délai n'est appliqué lorsque delay vaut zéro.
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
    vSecondResponse.headers = {}
    vSecondResponse.apparent_encoding = "utf-8"
    vSecondResponse.iter_content.return_value = [
        b"<html>Page 2</html>"
    ]

    mock_get.side_effect = [
        vFirstResponse,
        vSecondResponse
    ]

    vConfig = ScrapingConfig(
        delay=0
    )

    rHtml = fetch_page(
        "https://example.com",
        vConfig
    )

    assert rHtml == "<html>Page 2</html>"
    mock_sleep.assert_not_called()
    assert mock_get.call_count == 2