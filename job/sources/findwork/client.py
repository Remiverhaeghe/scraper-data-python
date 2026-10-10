"""Client HTTP de l'API Findwork"""

import requests

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

    try:
        vResponse = requests.get(API_URL, params=vParams, headers=vHeaders, timeout=10)

        vResponse.raise_for_status()

        vData = vResponse.json()

    except requests.RequestException as vException:
        logger.error("Erreur HTTP Findwork sur la page %s : %s", pPage, vException)
        raise

    except ValueError as vException:
        logger.error("Réponse JSON invalide de Findwork sur la page %s", pPage)
        raise ValueError("La réponse Findwork n'est pas un JSON valide") from vException

    rData = vData

    return rData
