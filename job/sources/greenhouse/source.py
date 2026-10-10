"""Déclaration de la source Greenhouse"""

from job.sources.config import SourceDefinition
from job.sources.greenhouse.config import load_config
from job.sources.greenhouse.service import scrape_jobs


def load_parameters(pJobConfig):
    """Charge les paramètres Greenhouse depuis l'environnement."""

    rParameters = {"board": load_config().board}

    return rParameters


def scrape(pParameters, pJobConfig):
    """Récupère les offres Greenhouse."""

    rDataFrame = scrape_jobs(pParameters["board"], pMaxItems=pJobConfig.max_items)

    return rDataFrame


SOURCE = SourceDefinition(
    name="greenhouse",
    label="Greenhouse",
    load_parameters=load_parameters,
    scrape=scrape,
)
