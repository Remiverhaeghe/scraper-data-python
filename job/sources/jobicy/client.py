"""Client HTTP de l'API publique Jobicy"""

import requests

from utils.api_client import request_json
from utils.logger import get_logger

logger = get_logger(__name__)

API_URL = "https://jobicy.com/api/v2/remote-jobs"

MAX_COUNT = 200


def get_jobs(pTag=None, pGeo=None, pCount=MAX_COUNT):
    """Récupère les offres en télétravail publiées sur Jobicy."""

    vParams = {"count": pCount}

    if pGeo:
        vParams["geo"] = pGeo

    if pTag:
        vParams["tag"] = pTag

    vHeaders = {"Accept": "application/json"}

    logger.info("Récupération des offres Jobicy : %s", vParams)

    try:
        vData = request_json(
            "GET", API_URL, pParams=vParams, pHeaders=vHeaders, pTimeout=10
        )

    except requests.RequestException as vException:
        logger.error("Erreur HTTP Jobicy : %s", vException)
        raise

    except ValueError as vException:
        logger.error("Appel refusé ou réponse invalide de Jobicy")
        raise ValueError(f"Jobicy : {vException}") from None

    rJobs = vData.get("jobs") or []

    return rJobs
