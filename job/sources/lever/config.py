# ============================================================================
# Configuration de la source Lever
# ============================================================================

import os
from dataclasses import dataclass


@dataclass
class LeverConfig:
    """
    Configuration nécessaire à l'utilisation de l'API Lever.
    """

    site: str


def load_config():
    """
    Charge la configuration Lever depuis les variables
    d'environnement.

    :return: Configuration Lever.
    """

    vSite = os.getenv(
        "LEVER_SITE"
    )

    if not vSite:
        raise ValueError(
            "Configuration Lever incomplète : "
            "LEVER_SITE"
        )

    vConfig = LeverConfig(
        site=vSite
    )

    rConfig = vConfig

    return rConfig