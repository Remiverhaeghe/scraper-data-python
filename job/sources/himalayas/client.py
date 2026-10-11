"""Client HTTP de l'API publique Himalayas"""

import requests

from utils.api_client import request_json
from utils.logger import get_logger

logger = get_logger(__name__)

API_URL = "https://himalayas.app/jobs/api/search"


def search_jobs(pQuery=None, pCountry=None, pPage=1):
    """Récupère une page de résultats de recherche Himalayas."""

    vParams = {"page": pPage}

    if pQuery:
        vParams["q"] = pQuery

    if pCountry:
        vParams["country"] = pCountry

    vHeaders = {"Accept": "application/json"}

    logger.info("Récupération des offres Himalayas : %s", vParams)

    # API publique sans clé ; 429 signale trop de requêtes rapprochées.
    try:
        vData = request_json(
            "GET", API_URL, pParams=vParams, pHeaders=vHeaders, pTimeout=10
        )

    except requests.RequestException as vException:
        logger.error("Erreur HTTP Himalayas sur la page %s : %s", pPage, vException)
        raise

    except ValueError as vException:
        logger.error(
            "Appel refusé ou réponse invalide d'Himalayas sur la page %s", pPage
        )
        raise ValueError(f"Himalayas : {vException}") from None

    rData = vData

    return rData
