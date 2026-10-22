"""Configuration de la source La bonne alternance"""

import os
from dataclasses import dataclass

# Codes métiers ROME cherchés par défaut : maintenance industrielle (I1304,
# I1310), automatisme (H1208), développement et exploitation informatique
# (M1805, M1810). L'API cherche par métier, pas par mot-clé.
DEFAULT_ROMES = "I1304,I1310,H1208,M1805,M1810"


@dataclass
class LaBonneAlternanceConfig:
    """Clé d'API et métiers cherchés."""

    api_key: str
    romes: str


def load_config():
    """Charge la configuration depuis les variables d'environnement."""

    vApiKey = os.getenv("LBA_API_KEY")

    if not vApiKey:
        raise ValueError("Configuration La bonne alternance incomplète : LBA_API_KEY")

    rConfig = LaBonneAlternanceConfig(
        api_key=vApiKey,
        romes=(os.getenv("LBA_ROMES") or DEFAULT_ROMES).replace(" ", ""),
    )

    return rConfig
