"""Tests de l'envoi d'e-mails"""

import smtplib

import pytest

from utils.mailer import get_missing_email_settings, send_email


class FakeSmtp:
    """Serveur SMTP simulé qui conserve les appels reçus."""

    instances = []

    def __init__(self, pHost, pPort, context, timeout):
        self.address = (pHost, pPort)
        self.credentials = None
        self.messages = []
        FakeSmtp.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *pArgs):
        return False

    def login(self, pUser, pPassword):
        self.credentials = (pUser, pPassword)

    def send_message(self, pMessage):
        self.messages.append(pMessage)


@pytest.fixture
def gmail_settings(monkeypatch):
    """Renseigne un compte Gmail fictif."""

    monkeypatch.setenv("GMAIL_ADDRESS", "envoi@gmail.com")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "mot-de-passe")


def test_missing_settings_prevent_sending(monkeypatch):
    """Vérifie qu'un envoi sans configuration nomme les variables manquantes."""

    monkeypatch.delenv("GMAIL_ADDRESS", raising=False)
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "mot-de-passe")

    assert get_missing_email_settings() == ["GMAIL_ADDRESS"]

    with pytest.raises(ValueError, match="GMAIL_ADDRESS"):
        send_email("moi@example.com", "Sujet", "Texte")


def test_send_email(gmail_settings, monkeypatch):
    """Vérifie la connexion chiffrée, l'authentification et le message envoyé."""

    FakeSmtp.instances.clear()
    monkeypatch.setattr(smtplib, "SMTP_SSL", FakeSmtp)

    send_email("moi@example.com", "Sujet", "Texte", "<p>Texte</p>")

    vServer = FakeSmtp.instances[0]
    vMessage = vServer.messages[0]

    assert vServer.address == ("smtp.gmail.com", 465)
    assert vServer.credentials == ("envoi@gmail.com", "mot-de-passe")
    assert vMessage["To"] == "moi@example.com"
    assert vMessage["From"] == "envoi@gmail.com"
    assert vMessage.get_body(("html",)).get_content().strip() == "<p>Texte</p>"
