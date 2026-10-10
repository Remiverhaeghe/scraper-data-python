"""Configuration commune des tests des sources d'offres"""

import pytest


@pytest.fixture(autouse=True)
def skip_dns_resolution(monkeypatch):
    """Évite la résolution DNS de validate_url : aucun test ne doit toucher le réseau."""

    monkeypatch.setattr("utils.api_client.validate_url", lambda pUrl: True)
