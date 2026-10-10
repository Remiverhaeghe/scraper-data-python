"""Déclaration de la source Arbeitnow"""

from job.sources.arbeitnow.service import scrape_jobs
from job.sources.config import SourceDefinition


def load_parameters(pJobConfig):
    """Construit les paramètres de recherche Arbeitnow."""

    rParameters = {"keyword": pJobConfig.keyword, "location": pJobConfig.location}

    return rParameters


def scrape(pParameters, pJobConfig):
    """Récupère les offres Arbeitnow."""

    rDataFrame = scrape_jobs(
        pParameters["keyword"],
        pParameters["location"],
        pMaxItems=pJobConfig.max_items,
        pMaxPages=pJobConfig.max_pages,
    )

    return rDataFrame


SOURCE = SourceDefinition(
    name="arbeitnow",
    label="Arbeitnow",
    load_parameters=load_parameters,
    scrape=scrape,
)
