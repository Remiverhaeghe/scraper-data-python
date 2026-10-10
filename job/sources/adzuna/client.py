"""Client HTTP de l'API Adzuna"""

import requests

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

    try:
        vResponse = requests.get(vUrl, params=vParams, headers=vHeaders, timeout=10)

        vResponse.raise_for_status()

        vData = vResponse.json()

    except requests.HTTPError:
        vMessage = f"Erreur HTTP Adzuna {vResponse.status_code} sur la page {pPage}"
        logger.error(vMessage)
        raise RuntimeError(vMessage) from None

    except requests.RequestException as vException:
        vMessage = (
            f"Erreur réseau Adzuna sur la page {pPage} : {type(vException).__name__}"
        )
        logger.error(vMessage)
        raise RuntimeError(vMessage) from None

    except ValueError:
        logger.error("Réponse JSON invalide d'Adzuna sur la page %s", pPage)
        raise ValueError("La réponse Adzuna n'est pas un JSON valide") from None

    rData = vData

    return rData
