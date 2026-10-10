"""Configuration de la source Jooble"""

import os
from dataclasses import dataclass


@dataclass
class JoobleConfig:
    """Configuration nécessaire à l'utilisation de l'API Jooble."""

    api_key: str


def load_config():
    """Charge la configuration Jooble depuis les variables d'environnement."""

    vApiKey = os.getenv("JOOBLE_API_KEY")

    if not vApiKey:
        raise ValueError("Configuration Jooble incomplète : JOOBLE_API_KEY")

    vConfig = JoobleConfig(api_key=vApiKey)

    rConfig = vConfig

    return rConfig
