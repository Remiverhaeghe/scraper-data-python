"""Tests de la création du certificat HTTPS du réseau local"""

import pytest

import tools.local_certificate as local_certificate


def test_local_address_needs_no_certificate(monkeypatch, capsys):
    """Vérifie le refus quand le tableau de bord n'écoute que sur ce PC."""

    monkeypatch.setattr(local_certificate, "WEB_HOST", "127.0.0.1")
    monkeypatch.setattr(
        local_certificate,
        "create_certificate",
        lambda *pArgs: pytest.fail("certificat créé"),
    )

    assert local_certificate.main() == 1
    assert "WEB_HOST n'est pas renseigné" in capsys.readouterr().out


def test_certificate_settings_are_shown(monkeypatch, capsys):
    """Vérifie l'empreinte et les réglages du .env affichés après la création."""

    vCalls = []
    monkeypatch.setattr(local_certificate, "WEB_HOST", "192.168.1.20")
    monkeypatch.setattr(
        local_certificate,
        "create_certificate",
        lambda *pArgs: vCalls.append(pArgs) or "AB:CD",
    )

    assert local_certificate.main() == 0

    vOutput = capsys.readouterr().out
    assert vCalls == [
        (
            "192.168.1.20",
            local_certificate.CERTIFICATE_FILE,
            local_certificate.KEY_FILE,
        )
    ]
    assert "AB:CD" in vOutput
    assert f"WEB_TLS_CERTFILE={local_certificate.CERTIFICATE_FILE}" in vOutput
