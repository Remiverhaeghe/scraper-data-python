"""Lancement du tableau de bord web avec python -m web"""

import ssl
import threading
import time
from pathlib import Path

import uvicorn

from config import WEB_HOST, WEB_PORT, WEB_SCHEME, WEB_TLS_CERTFILE, WEB_TLS_KEYFILE
from utils.logger import get_logger

logger = get_logger(__name__)

# Un certificat renouvelé par le planificateur est pris en compte dans l'heure.
CERTIFICATE_CHECK_SECONDS = 3600


def reload_certificate(pContext, pCertificateFile, pKeyFile, pLastModified):
    """Recharge le certificat dans le contexte TLS s'il a changé ; retourne sa date.

    Les connexions suivantes utilisent le nouveau certificat, sans redémarrage.
    """

    rModified = Path(pCertificateFile).stat().st_mtime

    if rModified != pLastModified:
        pContext.load_cert_chain(pCertificateFile, pKeyFile)
        logger.info("Certificat du tableau de bord rechargé")

    return rModified


def watch_certificate(pConfig):
    """Surveille le fichier du certificat tant que le serveur tourne."""

    vLastModified = Path(WEB_TLS_CERTFILE).stat().st_mtime

    while True:
        time.sleep(CERTIFICATE_CHECK_SECONDS)

        # Le contexte TLS n'existe qu'une fois le serveur démarré.
        vContext = getattr(pConfig, "ssl", None)

        if vContext is None:
            continue

        try:
            vLastModified = reload_certificate(
                vContext, WEB_TLS_CERTFILE, WEB_TLS_KEYFILE, vLastModified
            )

        except (OSError, ssl.SSLError) as vException:
            logger.warning(
                "Certificat renouvelé illisible, l'ancien reste : %s", vException
            )


if __name__ == "__main__":
    # Par défaut, WEB_HOST vaut 127.0.0.1 : le tableau de bord n'est joignable que
    # depuis ce PC. L'ouvrir au réseau suppose l'authentification configurée dans .env.
    # Avec WEB_TLS_CERTFILE et WEB_TLS_KEYFILE, il est servi en HTTPS.
    vConfig = uvicorn.Config(
        "web.app:app",
        host=WEB_HOST,
        port=WEB_PORT,
        ssl_certfile=WEB_TLS_CERTFILE if WEB_SCHEME == "https" else None,
        ssl_keyfile=WEB_TLS_KEYFILE if WEB_SCHEME == "https" else None,
    )

    if WEB_SCHEME == "https":
        threading.Thread(target=watch_certificate, args=(vConfig,), daemon=True).start()

    uvicorn.Server(vConfig).run()
