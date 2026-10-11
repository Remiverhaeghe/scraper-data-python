"""Client HTTP de l'API France Travail"""

import requests

from job.sources.france_travail.authentication import get_access_token
from utils.api_client import request_json
from utils.logger import get_logger

logger = get_logger(__name__)


def search_jobs(pConfig, pParams, pRange=None):
    """Recherche des offres d'emploi auprès de France Travail."""

    vAccessToken = get_access_token(pConfig)

    vHeaders = {"Authorization": f"Bearer {vAccessToken}", "Accept": "application/json"}

    vUrl = pConfig.api_base_url + "offresdemploi/v2/offres/search"

    vRequestParams = dict(pParams)

    if pRange is not None:
        vRequestParams["range"] = pRange

    logger.info("Recherche d'offres France Travail")

    # Dépannage : 401 signale un jeton refusé (identifiants FRANCE_TRAVAIL_* ou
    # portée FRANCE_TRAVAIL_SCOPE), 206 une réponse partielle normale paginée par range.
    try:
        vData = request_json("GET", vUrl, pParams=vRequestParams, pHeaders=vHeaders)
    except requests.RequestException:
        logger.exception("Erreur lors de la recherche France Travail")
        raise

    logger.info("Recherche France Travail terminée")

    rData = vData

    return rData
