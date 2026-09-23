# ============================================================================
# Client HTTP de l'API publique Lever
# ============================================================================

import requests

from utils.logger import get_logger


logger = get_logger(__name__)


def get_jobs(
    pSite,
    pLimit=100,
    pSkip=0
):
    """
    Récupère les offres publiées d'un site Lever.

    :param pSite: Identifiant du site Lever.
    :param pLimit: Nombre maximum d'offres demandées.
    :param pSkip: Nombre d'offres à ignorer.
    :return: Liste des offres.
    """

    vUrl = (
        "https://api.lever.co/v0/postings/"
        + pSite
    )

    vParams = {
        "mode": "json",
        "limit": pLimit,
        "skip": pSkip
    }

    vHeaders = {
        "Accept": "application/json"
    }

    logger.info(
        "Récupération des offres Lever : %s",
        pSite
    )

    try:
        vResponse = requests.get(
            vUrl,
            params=vParams,
            headers=vHeaders,
            timeout=10
        )

        vResponse.raise_for_status()

        vData = vResponse.json()

    except requests.RequestException as vException:
        logger.error(
            "Erreur HTTP Lever pour le site %s : %s",
            pSite,
            vException
        )
        raise

    except ValueError as vException:
        logger.error(
            "Réponse JSON invalide de Lever pour le site %s",
            pSite
        )
        raise ValueError(
            "La réponse Lever n'est pas un JSON valide"
        ) from vException

    rData = vData

    return rData