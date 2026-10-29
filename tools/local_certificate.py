"""Création du certificat HTTPS du tableau de bord sur le réseau local

    python -m tools.local_certificate

Le certificat couvre l'adresse WEB_HOST du .env. Les deux lignes affichées sont
à ajouter au .env, puis le serveur web est à relancer et le QR code à scanner
de nouveau depuis le téléphone.
"""

import sys
from pathlib import Path

from config import DATA_DIRECTORY, WEB_HOST
from utils.tls import create_certificate

TLS_DIRECTORY = DATA_DIRECTORY / "tls"
CERTIFICATE_FILE = TLS_DIRECTORY / "certificate.pem"
KEY_FILE = TLS_DIRECTORY / "private-key.pem"


def main():
    """Crée le certificat et indique les réglages à ajouter au .env."""

    if WEB_HOST in ("127.0.0.1", "localhost"):
        print(
            "WEB_HOST n'est pas renseigné dans .env : le tableau de bord n'écoute que "
            "sur ce PC, HTTPS n'y apporte rien."
        )
        return 1

    vFingerprint = create_certificate(WEB_HOST, CERTIFICATE_FILE, KEY_FILE)

    print(f"Certificat créé pour {WEB_HOST}, empreinte SHA-256 :")
    print(f"  {vFingerprint}")
    print("Ajouter au .env :")
    print(f"  WEB_TLS_CERTFILE={CERTIFICATE_FILE}")
    print(f"  WEB_TLS_KEYFILE={KEY_FILE}")
    print("Puis relancer python -m web et scanner de nouveau le QR code.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
