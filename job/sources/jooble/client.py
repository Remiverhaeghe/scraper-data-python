"""Client HTTP de l'API Jooble"""

import requests

from utils.logger import get_logger

logger = get_logger(__name__)

API_URL = "https://jooble.org/api/{key}"


def search_jobs(pConfig, pBody):
    """Récupère une page de résultats de recherche Jooble.

    La clé fait partie de l'URL : les messages d'erreur sont reconstruits
    sans elle pour qu'elle n'apparaisse ni dans les logs ni dans l'historique.
    """

    vUrl = API_URL.format(key=pConfig.api_key)

    logger.info("Récupération des offres Jooble : %s", pBody)

    try:
        vResponse = requests.post(vUrl, json=pBody, timeout=10)

        vResponse.raise_for_status()

        vData = vResponse.json()

    except requests.HTTPError:
        vMessage = f"Erreur HTTP Jooble {vResponse.status_code}"
        logger.error(vMessage)
        raise RuntimeError(vMessage) from None

    except requests.RequestException as vException:
        vMessage = f"Erreur réseau Jooble : {type(vException).__name__}"
        logger.error(vMessage)
        raise RuntimeError(vMessage) from None

    except ValueError:
        logger.error("Réponse JSON invalide de Jooble")
        raise ValueError("La réponse Jooble n'est pas un JSON valide") from None

    rData = vData

    return rData
