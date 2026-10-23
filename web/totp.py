"""Prépare la double authentification du tableau de bord : python -m web.totp

Crée un secret, enregistre son QR code à scanner avec une application comme
Google Authenticator, puis affiche la ligne à copier dans le fichier .env.
"""

import os
import sys
from pathlib import Path

import segno

from config import APPLICATION_NAME
from utils.totp import build_provisioning_uri, generate_secret

QR_FILE_NAME = "double-authentification.svg"


def main():
    """Crée le secret et son QR code, dans le dossier donné ou le dossier courant."""

    vDirectory = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    vSecret = generate_secret()
    vQrFile = vDirectory / QR_FILE_NAME

    segno.make(
        build_provisioning_uri(
            vSecret, os.getenv("WEB_USERNAME") or "tableau de bord", APPLICATION_NAME
        ),
        error="m",
    ).save(vQrFile, scale=6)

    print(f"QR code enregistré : {vQrFile}")
    print("Scannez-le avec l'application, puis supprimez ce fichier.")
    print("\nÀ copier dans le fichier .env, puis redémarrer le tableau de bord :")
    print(f"WEB_TOTP_SECRET={vSecret}")


if __name__ == "__main__":
    main()
