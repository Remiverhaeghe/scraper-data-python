"""Lancement du tableau de bord web avec python -m web"""

import uvicorn

from config import WEB_HOST, WEB_PORT, WEB_SCHEME, WEB_TLS_CERTFILE, WEB_TLS_KEYFILE

if __name__ == "__main__":
    # Par défaut, WEB_HOST vaut 127.0.0.1 : le tableau de bord n'est joignable que
    # depuis ce PC. L'ouvrir au réseau suppose l'authentification configurée dans .env.
    # Avec WEB_TLS_CERTFILE et WEB_TLS_KEYFILE, il est servi en HTTPS.
    uvicorn.run(
        "web.app:app",
        host=WEB_HOST,
        port=WEB_PORT,
        ssl_certfile=WEB_TLS_CERTFILE if WEB_SCHEME == "https" else None,
        ssl_keyfile=WEB_TLS_KEYFILE if WEB_SCHEME == "https" else None,
    )
