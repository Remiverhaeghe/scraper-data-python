"""Configuration commune à tous les tests"""

import pytest
import requests


def refuse_network_access(*pArgs, **pKwargs):
    """Remplace l'accès réseau réel pendant les tests."""

    raise RuntimeError(
        "Accès réseau réel interdit pendant les tests : simulez requests dans le test."
    )


@pytest.fixture(autouse=True)
def block_network(monkeypatch):
    """Bloque tout appel HTTP réel qu'un test aurait oublié de simuler.

    Les tests qui simulent requests.get, requests.post ou requests.request
    remplacent ces fonctions avant que la session réelle ne soit atteinte.
    """

    monkeypatch.setattr(requests.sessions.Session, "request", refuse_network_access)
