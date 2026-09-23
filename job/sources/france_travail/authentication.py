# ============================================================================
# Gestion de l'authentification OAuth2 France Travail
# ============================================================================

import requests

from utils.logger import get_logger

logger = get_logger(__name__)


def get_access_token(pConfig):
    """
    Récupère un jeton OAuth2 auprès de France Travail.

    :param pConfig: Configuration France Travail.
    :return: Jeton d'accès OAuth2.
    """

    logger.info(
        "Demande d'un jeton OAuth2 France Travail"
    )

    vData = {
        "grant_type": "client_credentials",
        "client_id": pConfig.client_id,
        "client_secret": pConfig.client_secret,
        "scope": pConfig.scope
    }

    try:
        vResponse = requests.post(
            pConfig.token_url,
            data=vData,
            timeout=10
        )
        vResponse.raise_for_status()
    except requests.RequestException:
        logger.exception(
            "Échec de l'authentification France Travail"
        )
        raise

    vTokenData = vResponse.json()
    vAccessToken = vTokenData.get("access_token")

    if not vAccessToken:
        raise ValueError(
            "Le serveur France Travail n'a pas retourné de jeton d'accès."
        )

    logger.info(
        "Authentification France Travail réussie"
    )

    rAccessToken = vAccessToken
    return rAccessToken