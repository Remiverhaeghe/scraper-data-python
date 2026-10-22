"""Client HTTP de l'API de recherche Careerjet (version 4)"""

import requests

from job.sources.careerjet.config import LOCALE_CODE, USER_AGENT
from utils.api_client import request_json
from utils.logger import get_logger

logger = get_logger(__name__)

API_URL = "https://search.api.careerjet.net/v4/query"

# Maximum accepté par l'API pour une page
PAGE_SIZE = 100


def search_jobs(pConfig, pKeyword, pLocation, pPage=1):
    """Retourne une page de résultats de recherche."""

    vParams = {
        "locale_code": LOCALE_CODE,
        "keywords": pKeyword or "",
        "location": pLocation or "",
        "sort": "date",
        "page": pPage,
        "page_size": PAGE_SIZE,
        "user_ip": pConfig.user_ip,
        "user_agent": USER_AGENT,
    }
    vHeaders = {"Referer": pConfig.referer} if pConfig.referer else None

    try:
        # Authentification de base : la clé d'éditeur, sans mot de passe.
        rData = request_json(
            "GET",
            API_URL,
            pParams=vParams,
            pHeaders=vHeaders,
            pAuth=(pConfig.api_key, ""),
        )
    except requests.HTTPError as vError:
        # La clé n'est jamais journalisée, seulement le code de l'erreur.
        logger.error(
            "Careerjet a refusé la recherche : HTTP %s",
            vError.response.status_code if vError.response is not None else "?",
        )
        raise

    return rData
