# ============================================================================
# Configuration de la source Greenhouse
# ============================================================================

import os
from dataclasses import dataclass


@dataclass
class GreenhouseConfig:
    """
    Configuration nécessaire à l'utilisation de l'API Greenhouse.
    """

    board: str


def load_config():
    """
    Charge la configuration Greenhouse depuis les variables
    d'environnement.

    :return: Configuration Greenhouse.
    """

    vBoard = os.getenv(
        "GREENHOUSE_BOARD"
    )

    if not vBoard:
        raise ValueError(
            "Configuration Greenhouse incomplète : "
            "GREENHOUSE_BOARD"
        )

    vConfig = GreenhouseConfig(
        board=vBoard
    )

    rConfig = vConfig

    return rConfig