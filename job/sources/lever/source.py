"""Déclaration de la source Lever"""

from job.sources.config import SourceDefinition, scrape_each
from job.sources.lever.config import load_config
from job.sources.lever.service import scrape_jobs


def load_parameters(pJobConfig):
    """Charge les paramètres Lever depuis l'environnement."""

    rParameters = {"site": load_config().site}

    return rParameters


def scrape(pParameters, pJobConfig):
    """Récupère les offres de chaque site Lever configuré."""

    rDataFrame = scrape_each(
        pParameters["site"],
        lambda pSite, pMaxItems: scrape_jobs(pSite, pMaxItems=pMaxItems),
        pJobConfig.max_items,
        "Lever",
    )

    return rDataFrame


SOURCE = SourceDefinition(
    name="lever",
    label="Lever",
    load_parameters=load_parameters,
    scrape=scrape,
    settings=("LEVER_SITE",),
)
