"""Configuration de la source Adzuna"""

import os
from dataclasses import dataclass

# Recherche limitée aux offres publiées en France
COUNTRY = "fr"


@dataclass
class AdzunaConfig:
    """Configuration nécessaire à l'utilisation de l'API Adzuna."""

    app_id: str
    app_key: str
    country: str = COUNTRY


def load_config():
    """Charge la configuration Adzuna depuis les variables d'environnement."""

    vAppId = os.getenv("ADZUNA_APP_ID")
    vAppKey = os.getenv("ADZUNA_APP_KEY")

    vMissing = [
        vName
        for vName, vValue in (("ADZUNA_APP_ID", vAppId), ("ADZUNA_APP_KEY", vAppKey))
        if not vValue
    ]

    if vMissing:
        raise ValueError("Configuration Adzuna incomplète : " + ", ".join(vMissing))

    vConfig = AdzunaConfig(app_id=vAppId, app_key=vAppKey)

    rConfig = vConfig

    return rConfig
