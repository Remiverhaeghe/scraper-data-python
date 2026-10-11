"""Configuration commune à tous les tests"""

import os
import smtplib
import tempfile
from datetime import datetime

# Avant tout import du code : les messages des tests, erreurs simulées comprises,
# ne doivent pas se mélanger aux journaux réels consultés dans l'application.
os.environ["LOG_DIRECTORY"] = tempfile.mkdtemp(prefix="jobboard-tests-logs-")

import pytest  # noqa: E402
import requests  # noqa: E402

from web.auth import (  # noqa: E402
    SESSION_COOKIE,
    hash_password,
    read_session_token,
)

TEST_PASSWORD = "mot-de-passe-de-test"


def refuse_network_access(*pArgs, **pKwargs):
    """Remplace l'accès réseau réel pendant les tests."""

    raise RuntimeError(
        "Accès réseau réel interdit pendant les tests : simulez requests dans le test."
    )


@pytest.fixture(autouse=True)
def block_network(monkeypatch):
    """Bloque tout appel HTTP ou SMTP réel qu'un test aurait oublié de simuler.

    Les tests qui simulent requests.get, requests.post ou requests.request
    remplacent ces fonctions avant que la session réelle ne soit atteinte.
    """

    monkeypatch.setattr(requests.sessions.Session, "request", refuse_network_access)
    monkeypatch.setattr(smtplib, "SMTP_SSL", refuse_network_access)


@pytest.fixture
def web_login(monkeypatch):
    """Configure un compte du tableau de bord et retourne de quoi s'y connecter."""

    from web.app import login_rate_limiter

    login_rate_limiter.failures.clear()

    monkeypatch.setenv("WEB_USERNAME", "admin")
    # Peu de tours de hachage : les tests restent rapides.
    monkeypatch.setenv("WEB_PASSWORD_HASH", hash_password(TEST_PASSWORD, 1000))
    monkeypatch.setenv("WEB_SESSION_SECRET", "secret-de-test")

    def login(pClient):
        """Ouvre une session et joint son jeton CSRF aux requêtes suivantes."""

        vResponse = pClient.post(
            "/login",
            data={"username": "admin", "password": TEST_PASSWORD},
            follow_redirects=False,
        )

        assert vResponse.status_code == 303

        vSession = read_session_token(
            "secret-de-test", pClient.cookies[SESSION_COOKIE], datetime.now()
        )
        pClient.headers["X-CSRF-Token"] = vSession["csrf"]

    return login
