"""Dépendances communes aux routes du tableau de bord et de l'API mobile"""

import hmac

from fastapi import HTTPException, Request

from config import DATABASE_FILE
from utils.logger import get_logger

logger = get_logger(__name__)


# Base de données : remplaçable dans les tests par app.dependency_overrides.
def get_database_file():
    """Retourne le chemin de la base, remplaçable dans les tests."""

    rDatabaseFile = DATABASE_FILE

    return rDatabaseFile


def get_csrf_token(pRequest):
    """Retourne le jeton CSRF de la session, à placer dans les formulaires."""

    vSession = getattr(pRequest.state, "session", None)

    rToken = vSession["csrf"] if vSession else ""

    return rToken


async def require_csrf(request: Request):
    """Refuse une requête d'écriture sans le jeton CSRF de la session."""

    vExpected = get_csrf_token(request)
    vToken = request.headers.get("X-CSRF-Token")

    if vToken is None:
        vToken = (await request.form()).get("csrf_token")

    if not vExpected or not vToken or not hmac.compare_digest(str(vToken), vExpected):
        logger.warning(
            "Requête refusée : jeton CSRF absent ou invalide sur %s", request.url.path
        )

        raise HTTPException(
            status_code=403, detail="Jeton de sécurité invalide : rechargez la page."
        )
