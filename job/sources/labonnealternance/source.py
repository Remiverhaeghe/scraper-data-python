"""Déclaration de la source La bonne alternance"""

from job.sources.boards import keep_board_jobs
from job.sources.config import SourceDefinition
from job.sources.labonnealternance.client import search_jobs
from job.sources.labonnealternance.config import load_config
from job.sources.labonnealternance.parser import parse_jobs
from utils.logger import get_logger

logger = get_logger(__name__)


def load_parameters(pJobConfig):
    """Construit les paramètres : clé, métiers et critères de recherche."""

    rParameters = {
        "config": load_config(),
        "keyword": pJobConfig.keyword,
        "location": pJobConfig.location,
    }

    return rParameters


def scrape(pParameters, pJobConfig):
    """Récupère les offres en alternance, puis garde celles qui correspondent."""

    vData = search_jobs(pParameters["config"])
    vJobs = parse_jobs(vData.get("jobs") or [])

    rJobs = keep_board_jobs(
        vJobs,
        set(),
        pParameters["keyword"],
        pParameters["location"],
        pJobConfig.max_items,
    )

    logger.info(
        "La bonne alternance : %s offre(s) reçue(s), %s retenue(s)",
        len(vJobs),
        len(rJobs),
    )

    return rJobs


SOURCE = SourceDefinition(
    name="labonnealternance",
    label="La bonne alternance",
    load_parameters=load_parameters,
    scrape=scrape,
    settings=("LBA_API_KEY",),
    category="france",
)
