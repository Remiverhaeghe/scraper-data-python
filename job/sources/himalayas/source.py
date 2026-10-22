"""Déclaration de la source Himalayas"""

from job.sources.config import SourceDefinition
from job.sources.himalayas.service import scrape_jobs


def load_parameters(pJobConfig):
    """Construit les paramètres de recherche Himalayas."""

    rParameters = {"query": pJobConfig.keyword}

    return rParameters


def scrape(pParameters, pJobConfig):
    """Récupère les offres Himalayas."""

    rDataFrame = scrape_jobs(
        pParameters["query"],
        pMaxItems=pJobConfig.max_items,
        pMaxPages=pJobConfig.max_pages,
    )

    return rDataFrame


SOURCE = SourceDefinition(
    name="himalayas",
    label="Himalayas",
    load_parameters=load_parameters,
    scrape=scrape,
    category="remote",
)
