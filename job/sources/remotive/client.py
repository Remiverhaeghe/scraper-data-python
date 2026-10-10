"""Client HTTP de l'API publique Remotive"""

import requests

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
        vResponse = requests.get(API_URL, params=vParams, headers=vHeaders, timeout=10)

        vResponse.raise_for_status()

        vData = vResponse.json()

    except requests.RequestException as vException:
        logger.error("Erreur HTTP Remotive : %s", vException)
        raise

    except ValueError as vException:
        logger.error("Réponse JSON invalide de Remotive")
        raise ValueError("La réponse Remotive n'est pas un JSON valide") from vException

    rJobs = vData.get("jobs") or []

    return rJobs
