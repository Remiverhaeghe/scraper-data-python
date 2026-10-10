"""Déclaration de la source Adzuna"""

from job.sources.adzuna.config import load_config
from job.sources.adzuna.service import scrape_jobs
from job.sources.config import SourceDefinition


def build_params(pJobConfig):
    """Construit les paramètres de recherche Adzuna.

    Le salaire n'est pas transmis : Adzuna filtre sur un brut annuel qui
    peut être estimé, alors que le filtre de l'application porte sur le net.
    """

    vParams = {"sort_by": "date"}

    if pJobConfig.keyword:
        vParams["what"] = pJobConfig.keyword

    if pJobConfig.location:
        vParams["where"] = pJobConfig.location

    if pJobConfig.max_distance_km is not None:
        vParams["distance"] = round(pJobConfig.max_distance_km)

    rParams = vParams

    return rParams


def load_parameters(pJobConfig):
    """Charge les identifiants et les paramètres de recherche Adzuna."""

    rParameters = {"config": load_config(), "params": build_params(pJobConfig)}

    return rParameters


def scrape(pParameters, pJobConfig):
    """Récupère les offres Adzuna."""

    rDataFrame = scrape_jobs(
        pParameters["config"],
        pParameters["params"],
        pMaxItems=pJobConfig.max_items,
        pMaxPages=pJobConfig.max_pages,
    )

    return rDataFrame


SOURCE = SourceDefinition(
    name="adzuna",
    label="Adzuna",
    load_parameters=load_parameters,
    scrape=scrape,
    settings=("ADZUNA_APP_ID", "ADZUNA_APP_KEY"),
)
