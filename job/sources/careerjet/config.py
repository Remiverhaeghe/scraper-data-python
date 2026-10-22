"""Configuration de la source Careerjet"""

import os
from dataclasses import dataclass

# Recherche en France, en français
LOCALE_CODE = "fr_FR"

# Careerjet demande l'adresse IP et le navigateur de l'utilisateur à l'origine de
# la recherche ; pour une application personnelle, ce poste.
DEFAULT_USER_IP = "127.0.0.1"
USER_AGENT = "JobBoardPerso/1.0"


@dataclass
class CareerjetConfig:
    """Clé d'éditeur et informations demandées par l'API."""

    api_key: str
    user_ip: str
    referer: str | None


def load_config():
    """Charge la configuration Careerjet depuis les variables d'environnement."""

    vApiKey = os.getenv("CAREERJET_API_KEY")

    if not vApiKey:
        raise ValueError("Configuration Careerjet incomplète : CAREERJET_API_KEY")

    rConfig = CareerjetConfig(
        api_key=vApiKey,
        user_ip=os.getenv("CAREERJET_USER_IP") or DEFAULT_USER_IP,
        # Adresse du site déclaré à l'inscription comme éditeur, si demandée
        referer=os.getenv("CAREERJET_REFERER") or None,
    )

    return rConfig
