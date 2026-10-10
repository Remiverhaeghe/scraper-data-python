"""Déclaration de la source Greenhouse"""

from job.sources.config import SourceDefinition, scrape_each
from job.sources.greenhouse.config import load_config
from job.sources.greenhouse.service import scrape_jobs


def load_parameters(pJobConfig):
    """Charge les paramètres Greenhouse depuis l'environnement."""

    rParameters = {"board": load_config().board}

    return rParameters


def scrape(pParameters, pJobConfig):
    """Récupère les offres de chaque board Greenhouse configuré."""

    rDataFrame = scrape_each(
        pParameters["board"],
        lambda pBoard, pMaxItems: scrape_jobs(pBoard, pMaxItems=pMaxItems),
        pJobConfig.max_items,
        "Greenhouse",
    )

    return rDataFrame


SOURCE = SourceDefinition(
    name="greenhouse",
    label="Greenhouse",
    load_parameters=load_parameters,
    scrape=scrape,
    settings=("GREENHOUSE_BOARD",),
)
