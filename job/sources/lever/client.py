"""Client HTTP de l'API publique Lever"""

import requests

from utils.api_client import request_json
from utils.logger import get_logger

logger = get_logger(__name__)


def get_jobs(pSite, pLimit=100, pSkip=0):
    """Récupère les offres publiées d'un site Lever."""

    vUrl = "https://api.lever.co/v0/postings/" + pSite

    vParams = {"mode": "json", "limit": pLimit, "skip": pSkip}

    vHeaders = {"Accept": "application/json"}

    logger.info("Récupération des offres Lever : %s", pSite)

    try:
        vData = request_json(
            "GET", vUrl, pParams=vParams, pHeaders=vHeaders, pTimeout=10
        )

    except requests.RequestException as vException:
        logger.error("Erreur HTTP Lever pour le site %s : %s", pSite, vException)
        raise

    except ValueError as vException:
        logger.error("Appel refusé ou réponse invalide de Lever pour le site %s", pSite)
        raise ValueError(f"Lever : {vException}") from None

    rData = vData

    return rData
