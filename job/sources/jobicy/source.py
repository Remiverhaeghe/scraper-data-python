"""Déclaration de la source Jobicy"""

from job.sources.config import SourceDefinition
from job.sources.jobicy.service import scrape_jobs


def load_parameters(pJobConfig):
    """Construit les paramètres de recherche Jobicy."""

    rParameters = {"tag": pJobConfig.keyword}

    return rParameters


def scrape(pParameters, pJobConfig):
    """Récupère les offres Jobicy."""

    rDataFrame = scrape_jobs(pParameters["tag"], pMaxItems=pJobConfig.max_items)

    return rDataFrame


SOURCE = SourceDefinition(
    name="jobicy",
    label="Jobicy",
    load_parameters=load_parameters,
    scrape=scrape,
)
