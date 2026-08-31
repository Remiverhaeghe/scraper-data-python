"""
Tests du client HTTP.
"""

import pytest
import requests

from scraper.http_client import fetch_page


def test_fetch_page_with_invalid_url():
    """Vérifie la gestion d'une erreur HTTP."""

    url = "https://example.com/page-inexistante"

    with pytest.raises(requests.HTTPError):
        fetch_page(url)