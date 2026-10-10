"""Client HTTP de l'API Algolia de Hacker News"""

import requests

from utils.logger import get_logger

logger = get_logger(__name__)

SEARCH_URL = "https://hn.algolia.com/api/v1/search_by_date"

ITEM_URL = "https://hn.algolia.com/api/v1/items/{id}"

# Le fil mensuel est publié par ce compte sous ce titre exact.
THREAD_AUTHOR = "whoishiring"
THREAD_TITLE = "Ask HN: Who is hiring?"


def get_json(pUrl, pParams=None):
    """Effectue une requête GET et retourne la réponse JSON."""

    try:
        vResponse = requests.get(pUrl, params=pParams, timeout=30)

        vResponse.raise_for_status()

        rData = vResponse.json()

    except requests.RequestException as vException:
        logger.error("Erreur HTTP Hacker News : %s", vException)
        raise

    except ValueError as vException:
        logger.error("Réponse JSON invalide de Hacker News : %s", pUrl)
        raise ValueError(
            "La réponse Hacker News n'est pas un JSON valide"
        ) from vException

    return rData


def find_latest_thread_id():
    """Retourne l'identifiant du dernier fil « Who is hiring? »."""

    vData = get_json(
        SEARCH_URL,
        {"tags": f"story,author_{THREAD_AUTHOR}", "query": "Who is hiring"},
    )

    rThreadId = None

    for vHit in vData.get("hits") or []:
        if (vHit.get("title") or "").startswith(THREAD_TITLE):
            rThreadId = vHit.get("objectID")
            break

    if rThreadId is None:
        raise ValueError("Aucun fil Hacker News « Who is hiring? » trouvé")

    logger.info("Fil Hacker News « Who is hiring? » : %s", rThreadId)

    return rThreadId


def get_thread(pThreadId):
    """Récupère un fil Hacker News avec ses commentaires."""

    logger.info("Récupération du fil Hacker News : %s", pThreadId)

    rThread = get_json(ITEM_URL.format(id=pThreadId))

    return rThread
