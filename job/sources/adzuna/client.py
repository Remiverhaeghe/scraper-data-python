"""Client HTTP de l'API Adzuna"""

import requests

from utils.api_client import request_json
from utils.logger import get_logger

logger = get_logger(__name__)

API_URL = "https://api.adzuna.com/v1/api/jobs/{country}/search/{page}"

RESULTS_PER_PAGE = 50


def search_jobs(pConfig, pParams, pPage, pResultsPerPage=RESULTS_PER_PAGE):
    """Récupère une page d'offres Adzuna.

    Les identifiants transitent dans l'URL : les messages d'erreur sont
    reconstruits sans elle pour qu'ils n'apparaissent ni dans les logs
    ni dans l'historique.
    """

    vUrl = API_URL.format(country=pConfig.country, page=pPage)

    vParams = {
        "app_id": pConfig.app_id,
        "app_key": pConfig.app_key,
        "results_per_page": pResultsPerPage,
        **pParams,
    }

    vHeaders = {"Accept": "application/json"}

    logger.info("Récupération des offres Adzuna : page %s", pPage)

    # Dépannage : 401 signale ADZUNA_APP_ID ou ADZUNA_APP_KEY invalide dans .env,
    # 429 le quota quotidien atteint (250 requêtes par jour en offre gratuite).
    try:
        vData = request_json(
            "GET", vUrl, pParams=vParams, pHeaders=vHeaders, pTimeout=10
        )

    except requests.HTTPError as vException:
        vMessage = (
            f"Erreur HTTP Adzuna {vException.response.status_code} sur la page {pPage}"
        )
        logger.error(vMessage)
        raise RuntimeError(vMessage) from None

    except requests.RequestException as vException:
        vMessage = (
            f"Erreur réseau Adzuna sur la page {pPage} : {type(vException).__name__}"
        )
        logger.error(vMessage)
        raise RuntimeError(vMessage) from None

    except ValueError as vException:
        logger.error("Appel refusé ou réponse invalide d'Adzuna sur la page %s", pPage)
        raise ValueError(f"Adzuna : {vException}") from None

    rData = vData

    return rData
