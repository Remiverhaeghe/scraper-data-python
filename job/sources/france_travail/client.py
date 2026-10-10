"""Client HTTP de l'API France Travail"""

import requests

from job.sources.france_travail.authentication import get_access_token
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

    try:
        vResponse = requests.get(
            vUrl, headers=vHeaders, params=vRequestParams, timeout=10
        )
        vResponse.raise_for_status()
    except requests.RequestException:
        logger.exception("Erreur lors de la recherche France Travail")
        raise

    vData = vResponse.json()

    logger.info("Recherche France Travail terminée")

    rData = vData

    return rData
