"""Client HTTP de l'API publique Arbeitnow"""

import requests

from utils.logger import get_logger

logger = get_logger(__name__)

API_URL = "https://www.arbeitnow.com/api/job-board-api"


def get_jobs(pPage=1):
    """Récupère une page d'offres publiées sur Arbeitnow."""

    vHeaders = {"Accept": "application/json"}

    logger.info("Récupération des offres Arbeitnow : page %s", pPage)

    try:
        vResponse = requests.get(
            API_URL, params={"page": pPage}, headers=vHeaders, timeout=10
        )

        vResponse.raise_for_status()

        vData = vResponse.json()

    except requests.RequestException as vException:
        logger.error("Erreur HTTP Arbeitnow sur la page %s : %s", pPage, vException)
        raise

    except ValueError as vException:
        logger.error("Réponse JSON invalide d'Arbeitnow sur la page %s", pPage)
        raise ValueError(
            "La réponse Arbeitnow n'est pas un JSON valide"
        ) from vException

    rData = vData

    return rData
