"""Certificat HTTPS reconnu pour un accès hors du domicile par Tailscale

    python -m tools.tailscale_certificate

Tailscale relie le téléphone au serveur (PC ou NAS) par un réseau privé chiffré,
sans ouvrir de port sur la box. La commande demande à Tailscale un certificat
Let's Encrypt pour le nom du serveur sur ce réseau (serveur.xxx.ts.net), puis
affiche les lignes à ajouter au .env. Le certificat vaut 90 jours : le
planificateur le renouvelle un mois avant sa fin, et le tableau de bord le
recharge sans redémarrer.

Prérequis, dans la console d'administration de Tailscale (DNS) : MagicDNS et
« HTTPS Certificates » activés.
"""

import sys
from pathlib import Path

from config import WEB_PORT
from utils.tailscale import read_server_identity, request_certificate

TLS_DIRECTORY = Path(__file__).resolve().parent.parent / "data" / "tls"
CERTIFICATE_FILE = TLS_DIRECTORY / "tailscale-certificate.pem"
KEY_FILE = TLS_DIRECTORY / "tailscale-private-key.pem"


def main():
    """Demande le certificat et indique les réglages à ajouter au .env."""

    try:
        vName, vAddress = read_server_identity()
        TLS_DIRECTORY.mkdir(parents=True, exist_ok=True)
        request_certificate(vName, CERTIFICATE_FILE, KEY_FILE)

    except (RuntimeError, OSError, ValueError) as vError:
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
