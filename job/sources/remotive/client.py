"""Client HTTP de l'API publique Remotive"""

import requests

from utils.api_client import request_json
from utils.logger import get_logger

logger = get_logger(__name__)

API_URL = "https://remotive.com/api/remote-jobs"


def get_jobs(pSearch=None, pLimit=None):
    """Récupère les offres en télétravail publiées sur Remotive."""

    vParams = {}

    if pSearch:
        vParams["search"] = pSearch

    if pLimit is not None:
        vParams["limit"] = pLimit

    vHeaders = {"Accept": "application/json"}

    logger.info("Récupération des offres Remotive : %s", vParams)

    try:
        vData = request_json(
            "GET", API_URL, pParams=vParams, pHeaders=vHeaders, pTimeout=10
        )

    except requests.RequestException as vException:
        logger.error("Erreur HTTP Remotive : %s", vException)
        raise

    except ValueError as vException:
        logger.error("Appel refusé ou réponse invalide de Remotive")
        raise ValueError(f"Remotive : {vException}") from None

    rJobs = vData.get("jobs") or []

    return rJobs
