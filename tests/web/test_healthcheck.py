"""Tests du contrôle de santé du conteneur"""

import web.healthcheck as healthcheck


class FakeResponse:
    """Réponse HTTP simulée, utilisable avec with."""

    def __init__(self, pStatus):
        self.status = pStatus

    def __enter__(self):
        return self

    def __exit__(self, *_pArgs):
        return False


def test_health_follows_the_ping_answer(monkeypatch):
    """Vérifie 0 quand le ping répond, 1 sinon ou sans réponse."""

    vUrls = []

    def answer(pUrl, **_pOptions):
        vUrls.append(pUrl)
        return FakeResponse(200)

    monkeypatch.setattr(healthcheck.urllib.request, "urlopen", answer)

    assert healthcheck.check_health() == 0
    assert vUrls[0].endswith("://127.0.0.1:8000/api/v1/ping")

    monkeypatch.setattr(
        healthcheck.urllib.request,
        "urlopen",
        lambda *pArgs, **pOptions: FakeResponse(503),
    )

    assert healthcheck.check_health() == 1

    def refuse(*_pArgs, **_pOptions):
        raise OSError("connexion refusée")

    monkeypatch.setattr(healthcheck.urllib.request, "urlopen", refuse)

    assert healthcheck.check_health() == 1
