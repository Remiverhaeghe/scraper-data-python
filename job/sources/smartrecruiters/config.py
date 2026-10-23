"""Configuration de la source SmartRecruiters"""

import os
from dataclasses import dataclass

from job.company_pages import load_company_list

# Pays des offres, au format ISO à deux lettres en minuscules
DEFAULT_COUNTRY = "fr"


@dataclass
class SmartRecruitersConfig:
    """Entreprises suivies et pays des offres."""

    companies: str
    country: str


def load_config():
    """Charge les entreprises suivies (Paramètres, .env ou défaut) et le pays."""

    rConfig = SmartRecruitersConfig(
        companies=load_company_list("smartrecruiters"),
        country=(os.getenv("SMARTRECRUITERS_COUNTRY") or DEFAULT_COUNTRY).lower(),
    )

    return rConfig
