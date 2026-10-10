"""Déclaration de la source Remotive"""

from job.sources.config import SourceDefinition
from job.sources.remotive.service import scrape_jobs


def load_parameters(pJobConfig):
    """Construit les paramètres de recherche Remotive."""

    rParameters = {"search": pJobConfig.keyword}

    return rParameters


def scrape(pParameters, pJobConfig):
    """Récupère les offres Remotive."""

    rDataFrame = scrape_jobs(pParameters["search"], pMaxItems=pJobConfig.max_items)

    return rDataFrame


SOURCE = SourceDefinition(
    name="remotive",
    label="Remotive",
    load_parameters=load_parameters,
    scrape=scrape,
)
