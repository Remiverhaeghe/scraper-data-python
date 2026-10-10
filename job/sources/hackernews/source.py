"""Déclaration de la source Hacker News"""

from job.sources.config import SourceDefinition
from job.sources.hackernews.service import scrape_jobs


def load_parameters(pJobConfig):
    """Construit les critères appliqués localement aux offres Hacker News."""

    rParameters = {"keyword": pJobConfig.keyword, "location": pJobConfig.location}

    return rParameters


def scrape(pParameters, pJobConfig):
    """Récupère les offres du dernier fil Hacker News."""

    rDataFrame = scrape_jobs(
        pParameters["keyword"],
        pParameters["location"],
        pMaxItems=pJobConfig.max_items,
    )

    return rDataFrame


SOURCE = SourceDefinition(
    name="hackernews",
    label="Hacker News",
    load_parameters=load_parameters,
    scrape=scrape,
)
