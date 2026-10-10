"""Déclaration de la source France Travail"""

from job.sources.config import SourceDefinition
from job.sources.france_travail.config import load_config
from job.sources.france_travail.service import scrape_jobs
from utils.logger import get_logger

logger = get_logger(__name__)


def build_params(pJobConfig):
    """Construit les paramètres de recherche France Travail.

    Seuls les paramètres dont le mapping avec l'API est actuellement
    défini dans le projet sont construits ici.
    """

    vParams = {}

    if pJobConfig.keyword:
        vParams["motsCles"] = pJobConfig.keyword

    logger.info("Paramètres France Travail : %s", vParams)

    rParams = vParams

    return rParams


def load_parameters(pJobConfig):
    """Charge les identifiants et les paramètres de recherche France Travail."""

    rParameters = {"config": load_config(), "params": build_params(pJobConfig)}

    return rParameters


def scrape(pParameters, pJobConfig):
    """Récupère les offres France Travail."""

    rDataFrame = scrape_jobs(
        pParameters["config"],
        pParameters["params"],
        pMaxItems=pJobConfig.max_items,
        pMaxPages=pJobConfig.max_pages,
    )

    return rDataFrame


SOURCE = SourceDefinition(
    name="france-travail",
    label="France Travail",
    load_parameters=load_parameters,
    scrape=scrape,
    # API suspendue par France Travail, accès soumis à une demande
    available=False,
)
