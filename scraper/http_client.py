# ============================================================================
# Gestion des requêtes HTTP du scraper
# ============================================================================


import requests

from utils.logger import get_logger


logger = get_logger(__name__)


def fetch_page(pUrl, pTimeout):
    """
    Récupère le contenu HTML d'une page web.

    :param pUrl: URL de la page à récupérer.
    :param pTimeout: Temps maximum d'attente de la requête.
    :return: Contenu HTML.
    """

    logger.info(
        "Récupération de la page : %s",
        pUrl
    )

    try:
        vResponse = requests.get(
            pUrl,
            timeout=pTimeout
        )

        vResponse.raise_for_status()

        vResponse.encoding = vResponse.apparent_encoding

    except requests.RequestException:
        logger.exception(
            "Échec de récupération : %s",
            pUrl
        )
        raise

    logger.info(
        "Page récupérée avec succès : %s",
        pUrl
    )

    rHtml = vResponse.text

    return rHtml