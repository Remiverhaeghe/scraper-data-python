"""Configuration de la source Findwork"""

import os
from dataclasses import dataclass


@dataclass
class FindworkConfig:
    """Configuration nécessaire à l'utilisation de l'API Findwork."""

    api_key: str


def load_config():
    """Charge la configuration Findwork depuis les variables d'environnement."""

    vApiKey = os.getenv("FINDWORK_API_KEY")

    if not vApiKey:
        raise ValueError("Configuration Findwork incomplète : FINDWORK_API_KEY")

    vConfig = FindworkConfig(api_key=vApiKey)

    rConfig = vConfig

    return rConfig
