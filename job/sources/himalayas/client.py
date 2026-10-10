"""Client HTTP de l'API publique Himalayas"""

import requests

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

    try:
        vResponse = requests.get(API_URL, params=vParams, headers=vHeaders, timeout=10)

        vResponse.raise_for_status()

        vData = vResponse.json()

    except requests.RequestException as vException:
        logger.error("Erreur HTTP Himalayas sur la page %s : %s", pPage, vException)
        raise

    except ValueError as vException:
        logger.error("Réponse JSON invalide d'Himalayas sur la page %s", pPage)
        raise ValueError(
            "La réponse Himalayas n'est pas un JSON valide"
        ) from vException

    rData = vData

    return rData
