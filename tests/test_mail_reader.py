"""Tests de la lecture des messages Gmail"""

import imaplib
from datetime import datetime

import pytest

import utils.mail_reader as mail_reader
from utils.mail_reader import read_recent_messages

NOW = datetime(2026, 10, 23, 12, 0)


def build_raw(pNumber):
    """Construit un message brut numéroté."""

    rRaw = (
        f"Message-ID: <{pNumber}@exemple.fr>\r\n"
        f"From: recruteur@exemple.fr\r\n"
        f"Subject: Message {pNumber}\r\n\r\nTexte {pNumber}"
    ).encode()

    return rRaw


class FakeImap:
    """Serveur IMAP simulé qui conserve les appels reçus."""

    instances = []

    def __init__(self, pHost, pPort, ssl_context, timeout):
        self.address = (pHost, pPort)
        self.context = ssl_context
        self.timeout = timeout
        self.credentials = None
        self.selected = None
        self.search_criteria = None
        self.fetched = []
        FakeImap.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *pArgs):
        return False

    def login(self, pUser, pPassword):
        self.credentials = (pUser, pPassword)

    def select(self, pMailbox, readonly):
        self.selected = (pMailbox, readonly)

    def search(self, _pCharset, *pCriteria):
        self.search_criteria = pCriteria

        return "OK", [b"1 2 3 4"]

    def fetch(self, pId, pQuery):
        self.fetched.append((pId, pQuery))

        # Le message 2 a disparu entre la recherche et la lecture.
        if pId == b"2":
            return "OK", [b")"]

        return "OK", [(b"header", build_raw(pId.decode())), b")"]


@pytest.fixture(name="fake_imap")
def fixture_fake_imap(monkeypatch):
    """Renseigne un compte Gmail fictif et remplace le serveur IMAP."""

    monkeypatch.setenv("GMAIL_ADDRESS", "lecture@gmail.com")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "mot-de-passe")
    monkeypatch.setattr(imaplib, "IMAP4_SSL", FakeImap)
    FakeImap.instances.clear()


def test_missing_settings_prevent_reading(monkeypatch):
    """Vérifie qu'une lecture sans configuration nomme les variables manquantes."""

    monkeypatch.delenv("GMAIL_ADDRESS", raising=False)
    monkeypatch.delenv("GMAIL_APP_PASSWORD", raising=False)

    with pytest.raises(ValueError, match="GMAIL_ADDRESS, GMAIL_APP_PASSWORD"):
        read_recent_messages(NOW, 7)


@pytest.mark.usefixtures("fake_imap")
def test_inbox_is_read_without_marking_messages():
    """Vérifie la connexion chiffrée, la lecture seule et les messages laissés non lus."""

    vMessages = read_recent_messages(NOW, 7)
    vServer = FakeImap.instances[0]

    assert vServer.address == ("imap.gmail.com", 993)
    assert vServer.context is not None
    assert vServer.timeout == 30
    assert vServer.credentials == ("lecture@gmail.com", "mot-de-passe")
    assert vServer.selected == ("INBOX", True)
    assert vServer.search_criteria == ("SINCE", "16-Oct-2026")
    assert {vQuery for _, vQuery in vServer.fetched} == {"(BODY.PEEK[])"}
    assert [vMessage["subject"] for vMessage in vMessages] == [
        "Message 4",
        "Message 3",
        "Message 1",
    ]


@pytest.mark.usefixtures("fake_imap")
def test_only_most_recent_messages_are_read(monkeypatch):
    """Vérifie que seuls les MAX_MESSAGES derniers messages sont lus."""

    monkeypatch.setattr(mail_reader, "MAX_MESSAGES", 2)

    vMessages = read_recent_messages(NOW, 7)

    assert [vId for vId, _ in FakeImap.instances[0].fetched] == [b"4", b"3"]
    assert [vMessage["message_id"] for vMessage in vMessages] == [
        "<4@exemple.fr>",
        "<3@exemple.fr>",
    ]
