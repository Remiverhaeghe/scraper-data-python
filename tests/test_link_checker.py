"""Tests de la vérification du lien d'une offre"""

import pytest
import requests

import utils.link_checker as link_checker
from utils.link_checker import check_offer_link, is_parent_page

OFFER_URL = "https://jobs.example.com/offres/123-developpeur"


class FakeResponse:
    """Réponse HTTP simulée, avec ou sans redirection."""

    def __init__(self, pStatus, pLocation=None):
        self.status_code = pStatus
        self.headers = {"Location": pLocation} if pLocation else {}
        self.is_redirect = pLocation is not None

    def close(self):
        """Rien à libérer pour une réponse simulée."""


@pytest.fixture(autouse=True)
def allow_test_urls(monkeypatch):
    """Évite la résolution DNS réelle de validate_url."""

    monkeypatch.setattr(link_checker, "validate_url", lambda pUrl: True)


def simulate(pMonkeypatch, *pResponses):
    """Fait renvoyer les réponses données, dans l'ordre, par requests.get."""

    vResponses = iter(pResponses)

    pMonkeypatch.setattr(
        link_checker.requests, "get", lambda *pArgs, **pKwargs: next(vResponses)
    )


@pytest.mark.parametrize(
    "pResponses, pExpected",
    [
        ([FakeResponse(200)], "available"),
        ([FakeResponse(404)], "expired"),
        ([FakeResponse(410)], "expired"),
        ([FakeResponse(403)], None),
        ([FakeResponse(503)], None),
        ([FakeResponse(301, "/offres")], "expired"),
        ([FakeResponse(302, "https://jobs.example.com/")], "expired"),
        (
            [FakeResponse(301, "/offres/123-developpeur-lille"), FakeResponse(200)],
            "available",
        ),
    ],
)
def test_check_offer_link(monkeypatch, pResponses, pExpected):
    """Vérifie la conclusion tirée de chaque réponse ou redirection."""

    simulate(monkeypatch, *pResponses)

    assert check_offer_link(OFFER_URL) == pExpected


def test_check_offer_link_without_answer(monkeypatch):
    """Vérifie qu'une erreur réseau ne permet pas de conclure."""

    def refuse(*pArgs, **pKwargs):
        raise requests.ConnectionError("hors ligne")

    monkeypatch.setattr(link_checker.requests, "get", refuse)

    assert check_offer_link(OFFER_URL) is None


def test_check_offer_link_rejects_internal_redirect(monkeypatch):
    """Vérifie qu'une redirection vers une adresse refusée arrête la vérification."""

    def validate(pUrl):
        if "127.0.0.1" in pUrl:
            raise ValueError("La destination réseau n'est pas autorisée.")
        return True

    monkeypatch.setattr(link_checker, "validate_url", validate)
    simulate(monkeypatch, FakeResponse(302, "http://127.0.0.1/admin"))

    assert check_offer_link(OFFER_URL) is None


@pytest.mark.parametrize(
    "pTarget, pParent",
    [
        ("https://jobs.example.com/offres", True),
        ("https://jobs.example.com/", True),
        ("https://jobs.example.com/offres/123-developpeur-lille", False),
        ("https://autre.example.com/offres", False),
    ],
)
def test_is_parent_page(pTarget, pParent):
    """Vérifie la détection d'une redirection vers une page parente."""

    assert is_parent_page(pTarget, OFFER_URL) is pParent
