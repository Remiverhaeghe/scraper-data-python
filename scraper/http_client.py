"""
Gestion des requêtes HTTP du scraper.
"""

import requests

from utils.logger import get_logger
from config import REQUEST_TIMEOUT

logger = get_logger(__name__)

def fetch_page(url):
    """
    Récupère le contenu HTML d'une page web.

    :param url: URL de la page à récupérer.
    :return: Contenu HTML.
    """
    logger.info("Récupération de la page : %s", url)

    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()

        response.encoding = response.apparent_encoding

    except requests.RequestException:
        logger.exception("Échec de récupération : %s", url)
        raise


    logger.info("Page récupérée avec succès : %s", url)

    return response.text