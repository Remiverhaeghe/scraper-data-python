"""Client HTTP de l'API publique Greenhouse"""

import requests

from utils.api_client import request_json
from utils.logger import get_logger

logger = get_logger(__name__)


def get_jobs(pBoardToken):
    """Récupère les offres d'emploi d'un board Greenhouse."""

    vUrl = "https://boards-api.greenhouse.io/v1/boards/" f"{pBoardToken}/jobs"

    logger.info("Récupération des offres Greenhouse")

    try:
        vData = request_json("GET", vUrl, pParams={"content": "true"})
    except requests.RequestException:
        logger.exception("Erreur lors de la récupération Greenhouse")
        raise

    logger.info("Récupération Greenhouse terminée")

    rData = vData
    return rData
