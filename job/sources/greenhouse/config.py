"""Configuration de la source Greenhouse"""

from dataclasses import dataclass

from job.company_pages import load_company_list


@dataclass
class GreenhouseConfig:
    """Configuration nécessaire à l'utilisation de l'API Greenhouse."""

    board: str


def load_config():
    """Charge les boards suivis : Paramètres, sinon GREENHOUSE_BOARD du .env."""

    vBoard = load_company_list("greenhouse")

    if not vBoard:
        raise ValueError("Configuration Greenhouse incomplète : GREENHOUSE_BOARD")

    vConfig = GreenhouseConfig(board=vBoard)

    rConfig = vConfig

    return rConfig
