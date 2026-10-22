"""Configuration de la source SmartRecruiters"""

import os
from dataclasses import dataclass

# Entreprises suivies par défaut, vérifiées sur l'API : ingénierie, industrie,
# contrôle qualité, location de matériel et jeu vidéo, avec des offres en France.
DEFAULT_COMPANIES = (
    "Alten,Assystem,Eurofins,Loxam,Trigo,BoschGroup,SaintGobain,Ubisoft2"
)

# Pays des offres, au format ISO à deux lettres en minuscules
DEFAULT_COUNTRY = "fr"


@dataclass
class SmartRecruitersConfig:
    """Entreprises suivies et pays des offres."""

    companies: str
    country: str


def load_config():
    """Charge la configuration, avec les entreprises par défaut si .env n'en donne pas."""

    rConfig = SmartRecruitersConfig(
        companies=os.getenv("SMARTRECRUITERS_COMPANIES") or DEFAULT_COMPANIES,
        country=(os.getenv("SMARTRECRUITERS_COUNTRY") or DEFAULT_COUNTRY).lower(),
    )

    return rConfig
