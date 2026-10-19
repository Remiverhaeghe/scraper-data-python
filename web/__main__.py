"""Lancement du tableau de bord web avec python -m web"""

import uvicorn

from config import WEB_HOST, WEB_PORT

if __name__ == "__main__":
    # Par défaut, WEB_HOST vaut 127.0.0.1 : le tableau de bord n'est joignable que
    # depuis ce PC. L'ouvrir au réseau suppose l'authentification configurée dans .env.
    uvicorn.run("web.app:app", host=WEB_HOST, port=WEB_PORT)
