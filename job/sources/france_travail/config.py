# ============================================================================
# Configuration de la source France Travail
# ============================================================================

import os
from dataclasses import dataclass


@dataclass
class FranceTravailConfig:
    """
    Configuration nécessaire à l'utilisation de l'API France Travail.
    """

    client_id: str
    client_secret: str
    scope: str
    token_url: str
    api_base_url: str


def load_config():
    """
    Charge la configuration France Travail depuis les variables
    d'environnement.

    :return: Configuration France Travail.
    """

    vClientId = os.getenv(
        "FRANCE_TRAVAIL_CLIENT_ID"
    )

    vClientSecret = os.getenv(
        "FRANCE_TRAVAIL_CLIENT_SECRET"
    )

    vScope = os.getenv(
        "FRANCE_TRAVAIL_SCOPE"
    )

    vTokenUrl = os.getenv(
        "FRANCE_TRAVAIL_TOKEN_URL"
    )

    vApiBaseUrl = os.getenv(
        "FRANCE_TRAVAIL_API_BASE_URL"
    )

    vMissingValues = []

    if not vClientId:
        vMissingValues.append(
            "FRANCE_TRAVAIL_CLIENT_ID"
        )

    if not vClientSecret:
        vMissingValues.append(
            "FRANCE_TRAVAIL_CLIENT_SECRET"
        )

    if not vScope:
        vMissingValues.append(
            "FRANCE_TRAVAIL_SCOPE"
        )

    if not vTokenUrl:
        vMissingValues.append(
            "FRANCE_TRAVAIL_TOKEN_URL"
        )

    if not vApiBaseUrl:
        vMissingValues.append(
            "FRANCE_TRAVAIL_API_BASE_URL"
        )

    if vMissingValues:
        raise ValueError(
            "Configuration France Travail incomplète : "
            + ", ".join(vMissingValues)
        )

    vConfig = FranceTravailConfig(
        client_id=vClientId,
        client_secret=vClientSecret,
        scope=vScope,
        token_url=vTokenUrl,
        api_base_url=vApiBaseUrl
    )

    rConfig = vConfig

    return rConfig