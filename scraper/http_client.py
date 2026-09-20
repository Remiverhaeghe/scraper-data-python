# ============================================================================
# Gestion des requêtes HTTP du scraper
# ============================================================================


import requests

from utils.logger import get_logger
from utils.security import validate_url


logger = get_logger(__name__)


MAX_REDIRECTS = 5


def fetch_page(pUrl, pTimeout):
    """
    Récupère le contenu HTML d'une page web.

    :param pUrl: URL de la page à récupérer.
    :param pTimeout: Temps maximum d'attente de la requête.
    :return: Contenu HTML.
    """

    logger.info("Récupération de la page : %s", pUrl)

    vCurrentUrl = pUrl
    vRedirectCount = 0
    vResponse = None

    while vCurrentUrl:
        validate_url(vCurrentUrl)

        try:
            vResponse = requests.get(
                vCurrentUrl,
                timeout=pTimeout,
                allow_redirects=False
            )
        except requests.RequestException:
            logger.exception(
                "Échec de récupération : %s",
                vCurrentUrl
            )
            raise

        if not vResponse.is_redirect:
            break

        vRedirectCount += 1

        if vRedirectCount > MAX_REDIRECTS:
            raise ValueError(
                "Nombre maximum de redirections dépassé."
            )

        vCurrentUrl = vResponse.headers.get("Location")

        if not vCurrentUrl:
            raise ValueError(
                "La redirection ne contient pas de destination."
            )

        logger.info(
            "Redirection détectée vers : %s",
            vCurrentUrl
        )

    vResponse.raise_for_status()
    vResponse.encoding = vResponse.apparent_encoding

    logger.info("Page récupérée avec succès : %s", vCurrentUrl)

    rHtml = vResponse.text
    return rHtml