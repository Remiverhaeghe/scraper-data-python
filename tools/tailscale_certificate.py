"""Certificat HTTPS reconnu pour un accès hors du domicile par Tailscale

    python -m tools.tailscale_certificate

Tailscale relie le téléphone au serveur (PC ou NAS) par un réseau privé chiffré,
sans ouvrir de port sur la box. La commande demande à Tailscale un certificat
Let's Encrypt pour le nom du serveur sur ce réseau (serveur.xxx.ts.net), puis
affiche les lignes à ajouter au .env. Le certificat vaut 90 jours : relancer la
commande chaque mois le renouvelle.

Prérequis, dans la console d'administration de Tailscale (DNS) : MagicDNS et
« HTTPS Certificates » activés.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

from config import WEB_PORT

TLS_DIRECTORY = Path(__file__).resolve().parent.parent / "data" / "tls"
CERTIFICATE_FILE = TLS_DIRECTORY / "tailscale-certificate.pem"
KEY_FILE = TLS_DIRECTORY / "tailscale-private-key.pem"

COMMAND_TIMEOUT = 120


def run_tailscale(pArguments):
    """Lance une commande tailscale ; retourne sa sortie, lève RuntimeError en échec."""

    vExecutable = shutil.which("tailscale")

    if vExecutable is None:
        raise RuntimeError(
            "Tailscale n'est pas installé sur ce poste : https://tailscale.com/download"
        )

    vResult = subprocess.run(
        [vExecutable, *pArguments],
        capture_output=True,
        text=True,
        timeout=COMMAND_TIMEOUT,
        check=False,
    )

    if vResult.returncode != 0:
        raise RuntimeError(
            f"tailscale {pArguments[0]} a échoué : {vResult.stderr.strip()}"
        )

    rOutput = vResult.stdout

    return rOutput


def read_server_identity():
    """Retourne le nom de ce poste sur le réseau Tailscale et son adresse IPv4."""

    vSelf = json.loads(run_tailscale(["status", "--json"])).get("Self") or {}
    vName = vSelf.get("DNSName", "").rstrip(".")
    vAddress = next(
        (vIp for vIp in vSelf.get("TailscaleIPs") or [] if "." in vIp), None
    )

    if not vName or not vAddress:
        raise RuntimeError(
            "Nom Tailscale inconnu : connecter ce poste (tailscale up) et activer "
            "MagicDNS dans la console d'administration."
        )

    rIdentity = (vName, vAddress)

    return rIdentity


def main():
    """Demande le certificat et indique les réglages à ajouter au .env."""

    try:
        vName, vAddress = read_server_identity()
        TLS_DIRECTORY.mkdir(parents=True, exist_ok=True)
        run_tailscale(
            [
                "cert",
                "--cert-file",
                str(CERTIFICATE_FILE),
                "--key-file",
                str(KEY_FILE),
                vName,
            ]
        )

    except (RuntimeError, OSError, ValueError, subprocess.TimeoutExpired) as vError:
        print(vError)
        return 1

    print(f"Certificat reçu pour {vName}.")
    print("Ajouter ou remplacer dans le .env :")
    # Écoute sur la seule adresse Tailscale : fermé au Wi-Fi et à Internet.
    print(f"  WEB_HOST={vAddress}")
    print(f"  WEB_PUBLIC_HOST={vName}")
    print(f"  WEB_TLS_CERTFILE={CERTIFICATE_FILE}")
    print(f"  WEB_TLS_KEYFILE={KEY_FILE}")
    print("  WEB_SECURE_COOKIE=1")
    print("Puis relancer python -m web et scanner de nouveau le QR code.")
    print(f"Tableau de bord, depuis un appareil du réseau : https://{vName}:{WEB_PORT}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
