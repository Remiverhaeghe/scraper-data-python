"""Contrôle de santé du conteneur : le tableau de bord répond-il ?

    python -m web.healthcheck

Interroge la route publique /api/v1/ping sur ce poste ; code de sortie 0 si elle
répond, 1 sinon. Utilisé par le HEALTHCHECK de l'image Docker.
"""

import ssl
import sys
import urllib.request

from config import WEB_PORT, WEB_SCHEME

TIMEOUT_SECONDS = 5


def check_health():
    """Retourne 0 si le tableau de bord répond, 1 sinon."""

    vUrl = f"{WEB_SCHEME}://127.0.0.1:{WEB_PORT}/api/v1/ping"

    # Le certificat couvre le nom public du serveur, pas 127.0.0.1 : la requête
    # ne quitte pas le conteneur, la vérification n'apporterait rien ici.
    vContext = ssl.create_default_context()
    vContext.check_hostname = False
    vContext.verify_mode = ssl.CERT_NONE

    try:
        with urllib.request.urlopen(  # nosec B310
            vUrl, timeout=TIMEOUT_SECONDS, context=vContext
        ) as vResponse:
            rCode = 0 if vResponse.status == 200 else 1

    except OSError:
        rCode = 1

    return rCode


if __name__ == "__main__":
    sys.exit(check_health())
