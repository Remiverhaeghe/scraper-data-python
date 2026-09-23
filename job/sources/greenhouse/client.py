# ============================================================================
# Client HTTP de l'API publique Greenhouse
# ============================================================================

import requests

from utils.logger import get_logger

logger = get_logger(__name__)


def get_jobs(pBoardToken):
    """
    Récupère les offres d'emploi d'un board Greenhouse.

    :param pBoardToken: Identifiant public du board Greenhouse.
    :return: Réponse JSON de Greenhouse.
    """

    vUrl = (
        "https://boards-api.greenhouse.io/v1/boards/"
        f"{pBoardToken}/jobs"
    )

    logger.info(
        "Récupération des offres Greenhouse"
    )

    try:
        vResponse = requests.get(
            vUrl,
            params={
                "content": "true"
            },
            timeout=10
        )
        vResponse.raise_for_status()
    except requests.RequestException:
        logger.exception(
            "Erreur lors de la récupération Greenhouse"
        )
        raise

    vData = vResponse.json()

    logger.info(
        "Récupération Greenhouse terminée"
    )

    rData = vData
    return rData