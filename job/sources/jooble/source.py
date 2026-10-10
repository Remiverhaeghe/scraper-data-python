"""Déclaration de la source Jooble"""

from job.sources.config import SourceDefinition
from job.sources.jooble.config import load_config
from job.sources.jooble.service import scrape_jobs


def build_params(pJobConfig):
    """Construit les critères de recherche Jooble."""

    rParams = {
        "keywords": pJobConfig.keyword,
        "location": pJobConfig.location,
        "radius": (
            round(pJobConfig.max_distance_km)
            if pJobConfig.max_distance_km is not None
            else None
        ),
    }

    return rParams


def load_parameters(pJobConfig):
    """Charge la clé et les critères de recherche Jooble."""

    rParameters = {"config": load_config(), "params": build_params(pJobConfig)}

    return rParameters


def scrape(pParameters, pJobConfig):
    """Récupère les offres Jooble."""

    rDataFrame = scrape_jobs(
        pParameters["config"],
        pParameters["params"],
        pMaxItems=pJobConfig.max_items,
        pMaxPages=pJobConfig.max_pages,
    )

    return rDataFrame


SOURCE = SourceDefinition(
    name="jooble",
    label="Jooble",
    load_parameters=load_parameters,
    scrape=scrape,
)
