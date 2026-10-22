"""Client HTTP de l'API La bonne alternance (api.apprentissage.beta.gouv.fr)"""

import requests

from utils.api_client import request_json
from utils.logger import get_logger

logger = get_logger(__name__)

API_URL = "https://api.apprentissage.beta.gouv.fr/api/job/v1/search"


def search_jobs(pConfig):
    """Retourne les offres en alternance des métiers configurés, dans toute la France."""

    try:
        # Sans coordonnées, la recherche couvre toute la France ; le lieu est
        # filtré ensuite comme pour les autres sources.
        rData = request_json(
            "GET",
            API_URL,
            pParams={"romes": pConfig.romes},
            pHeaders={"Authorization": f"Bearer {pConfig.api_key}"},
        )
    except requests.HTTPError as vError:
        # La clé n'est jamais journalisée, seulement le code de l'erreur.
        logger.error(
            "La bonne alternance a refusé la recherche : HTTP %s",
            vError.response.status_code if vError.response is not None else "?",
        )
        raise

    return rData
