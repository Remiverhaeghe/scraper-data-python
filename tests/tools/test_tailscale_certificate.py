"""Tests de la demande du certificat Tailscale"""

import json
import subprocess

import tools.tailscale_certificate as tailscale_certificate

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

    pMonkeypatch.setattr(tailscale_certificate.shutil, "which", lambda _pName: "ts")
    pMonkeypatch.setattr(tailscale_certificate.subprocess, "run", run)

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

    monkeypatch.setattr(tailscale_certificate.shutil, "which", lambda _pName: None)

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
