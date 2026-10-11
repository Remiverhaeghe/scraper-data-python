"""Client HTTP de l'API Findwork"""

import requests

from utils.api_client import request_json
from utils.logger import get_logger

logger = get_logger(__name__)

API_URL = "https://findwork.dev/api/jobs/"


def get_jobs(pConfig, pParams, pPage=1):
    """Récupère une page d'offres Findwork.

    La clé est transmise dans un en-tête, absent des messages d'erreur.
    """

    vHeaders = {
        "Accept": "application/json",
        "Authorization": f"Token {pConfig.api_key}",
    }

    vParams = {**pParams, "page": pPage}

    logger.info("Récupération des offres Findwork : %s", vParams)

    # Dépannage : 401 signale FINDWORK_API_KEY absente ou invalide dans .env,
    # 429 un nombre de requêtes trop élevé.
    try:
        vData = request_json(
            "GET", API_URL, pParams=vParams, pHeaders=vHeaders, pTimeout=10
        )

    except requests.RequestException as vException:
        logger.error("Erreur HTTP Findwork sur la page %s : %s", pPage, vException)
        raise

    except ValueError as vException:
        logger.error(
            "Appel refusé ou réponse invalide de Findwork sur la page %s", pPage
        )
        raise ValueError(f"Findwork : {vException}") from None

    rData = vData

    return rData
