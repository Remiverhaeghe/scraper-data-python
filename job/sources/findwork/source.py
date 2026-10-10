"""Déclaration de la source Findwork"""

from job.sources.config import SourceDefinition
from job.sources.findwork.config import load_config
from job.sources.findwork.service import scrape_jobs


def build_params(pJobConfig):
    """Construit les critères de recherche Findwork."""

    vParams = {}

    if pJobConfig.keyword:
        vParams["search"] = pJobConfig.keyword

    if pJobConfig.location:
        vParams["location"] = pJobConfig.location

    rParams = vParams

    return rParams


def load_parameters(pJobConfig):
    """Charge la clé et les critères de recherche Findwork."""

    rParameters = {"config": load_config(), "params": build_params(pJobConfig)}

    return rParameters


def scrape(pParameters, pJobConfig):
    """Récupère les offres Findwork."""

    rDataFrame = scrape_jobs(
        pParameters["config"],
        pParameters["params"],
        pMaxItems=pJobConfig.max_items,
        pMaxPages=pJobConfig.max_pages,
    )

    return rDataFrame


SOURCE = SourceDefinition(
    name="findwork",
    label="Findwork",
    load_parameters=load_parameters,
    scrape=scrape,
    settings=("FINDWORK_API_KEY",),
)
