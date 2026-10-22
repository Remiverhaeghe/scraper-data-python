"""Déclaration de la source Careerjet"""

import pandas as pd

from job.csv_schema import JOB_COLUMNS
from job.sources.careerjet.client import PAGE_SIZE, search_jobs
from job.sources.careerjet.config import load_config
from job.sources.careerjet.parser import parse_jobs
from job.sources.config import SourceDefinition
from utils.logger import get_logger

logger = get_logger(__name__)

# Pages lues au plus par recherche : 300 offres récentes
DEFAULT_MAX_PAGES = 3


def load_parameters(pJobConfig):
    """Construit les paramètres de recherche Careerjet."""

    rParameters = {
        "config": load_config(),
        "keyword": pJobConfig.keyword,
        "location": pJobConfig.location,
    }

    return rParameters


def scrape(pParameters, pJobConfig):
    """Récupère les offres Careerjet, page par page, jusqu'à la limite."""

    vMaxPages = pJobConfig.max_pages or DEFAULT_MAX_PAGES
    vFrames = []

    for vPage in range(1, vMaxPages + 1):
        vData = search_jobs(
            pParameters["config"],
            pParameters["keyword"],
            pParameters["location"],
            vPage,
        )
        vJobs = vData.get("jobs") or []
        vFrames.append(parse_jobs(vJobs))

        vCount = sum(map(len, vFrames))

        if (
            len(vJobs) < PAGE_SIZE
            or vPage >= (vData.get("pages") or 0)
            or (pJobConfig.max_items is not None and vCount >= pJobConfig.max_items)
        ):
            break

    vDataFrame = (
        pd.concat(vFrames, ignore_index=True)
        if vFrames
        else pd.DataFrame(columns=JOB_COLUMNS)
    )
    rDataFrame = vDataFrame.drop_duplicates("source_id").head(
        pJobConfig.max_items if pJobConfig.max_items is not None else len(vDataFrame)
    )

    logger.info("Careerjet : %s offre(s) récupérée(s)", len(rDataFrame))

    return rDataFrame


SOURCE = SourceDefinition(
    name="careerjet",
    label="Careerjet",
    load_parameters=load_parameters,
    scrape=scrape,
    settings=("CAREERJET_API_KEY",),
    category="france",
)
