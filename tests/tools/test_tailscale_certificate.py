"""Tests de la demande du certificat Tailscale"""

import json
import subprocess
from datetime import datetime, timedelta

import tools.tailscale_certificate as tailscale_certificate
import utils.tailscale as tailscale
from utils.tls import create_certificate, read_expiry

STATUS = {
    "Self": {
        "DNSName": "serveur.chat-tigre.ts.net.",
        "TailscaleIPs": ["fd7a:115c::1", "100.101.102.103"],
    }
}


def simulate(pMonkeypatch, pAnswers):
    """Remplace tailscale par des réponses (code, sortie) ; retourne les appels."""

    rCalls = []

    def run(pCommand, **_pOptions):
        rCalls.append(pCommand[1:])
        vCode, vOutput = pAnswers[pCommand[1]]

        return subprocess.CompletedProcess(pCommand, vCode, vOutput, vOutput)

    pMonkeypatch.setattr(tailscale.shutil, "which", lambda _pName: "ts")
    pMonkeypatch.setattr(tailscale.subprocess, "run", run)

    return rCalls


def test_certificate_is_requested_for_the_server_name(tmp_path, monkeypatch, capsys):
    """Vérifie la demande pour le nom Tailscale et les lignes du .env affichées."""

    monkeypatch.setattr(tailscale_certificate, "TLS_DIRECTORY", tmp_path)
    vCalls = simulate(monkeypatch, {"status": (0, json.dumps(STATUS)), "cert": (0, "")})

    assert tailscale_certificate.main() == 0
    assert vCalls[1][-1] == "serveur.chat-tigre.ts.net"
    vOutput = capsys.readouterr().out

    assert "WEB_PUBLIC_HOST=serveur.chat-tigre.ts.net" in vOutput
    assert "WEB_HOST=100.101.102.103" in vOutput


def test_missing_tailscale_or_https_is_explained(tmp_path, monkeypatch, capsys):
    """Vérifie les messages sans Tailscale, sans nom et sans certificats HTTPS."""

    monkeypatch.setattr(tailscale_certificate, "TLS_DIRECTORY", tmp_path)

    monkeypatch.setattr(tailscale.shutil, "which", lambda _pName: None)

    assert tailscale_certificate.main() == 1
    assert "pas installé" in capsys.readouterr().out

    simulate(monkeypatch, {"status": (0, json.dumps({"Self": {}}))})

    assert tailscale_certificate.main() == 1
    assert "MagicDNS" in capsys.readouterr().out

    simulate(
        monkeypatch,
        {
            "status": (0, json.dumps(STATUS)),
            "cert": (1, "HTTPS certificates are not enabled"),
        },
    )

    assert tailscale_certificate.main() == 1
    assert "not enabled" in capsys.readouterr().out


def test_certificate_is_renewed_a_month_before_its_end(tmp_path, monkeypatch, caplog):
    """Vérifie le renouvellement : nom Tailscale seulement, à un mois de la fin."""

    vCertificate = tmp_path / "certificate.pem"
    vKey = tmp_path / "key.pem"
    vNow = datetime(2026, 10, 23)
    create_certificate("127.0.0.1", vCertificate, vKey, vNow)
    vExpiry = read_expiry(vCertificate)
    vName = "serveur.chat-tigre.ts.net"
    vCalls = simulate(monkeypatch, {"cert": (0, "")})

    assert not tailscale.renew_certificate_if_due("pc.local", vCertificate, vKey, vNow)
    assert not tailscale.renew_certificate_if_due(vName, vCertificate, vKey, vNow)
    assert tailscale.renew_certificate_if_due(
        vName, vCertificate, vKey, vExpiry - timedelta(days=10)
    )
    assert tailscale.renew_certificate_if_due(vName, tmp_path / "absent", vKey, vNow)
    assert len(vCalls) == 2

    simulate(monkeypatch, {"cert": (1, "refusé")})

    assert not tailscale.renew_certificate_if_due(
        vName, vCertificate, vKey, vExpiry - timedelta(days=10)
    )
    assert "non renouvelé" in caplog.text


def test_silent_tailscale_is_reported(monkeypatch):
    """Vérifie qu'une commande tailscale bloquée devient une erreur lisible."""

    def wait(pCommand, **_pOptions):
        raise subprocess.TimeoutExpired(pCommand, 120)

    monkeypatch.setattr(tailscale.shutil, "which", lambda _pName: "ts")
    monkeypatch.setattr(tailscale.subprocess, "run", wait)

    assert tailscale_certificate.main() == 1
