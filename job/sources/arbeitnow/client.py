"""Client HTTP de l'API publique Arbeitnow"""

import requests

from utils.api_client import request_json
from utils.logger import get_logger

logger = get_logger(__name__)

API_URL = "https://www.arbeitnow.com/api/job-board-api"


def get_jobs(pPage=1):
    """Récupère une page d'offres publiées sur Arbeitnow."""

    vHeaders = {"Accept": "application/json"}

    logger.info("Récupération des offres Arbeitnow : page %s", pPage)

    try:
        vData = request_json(
            "GET", API_URL, pParams={"page": pPage}, pHeaders=vHeaders, pTimeout=10
        )

    except requests.RequestException as vException:
        logger.error("Erreur HTTP Arbeitnow sur la page %s : %s", pPage, vException)
        raise

    except ValueError as vException:
        logger.error(
            "Appel refusé ou réponse invalide d'Arbeitnow sur la page %s", pPage
        )
        raise ValueError(f"Arbeitnow : {vException}") from None

    rData = vData

    return rData
