from job.parser import (
    extract_job,
    extract_jobs,
    extract_next_url,
    parse_html
)
from scraper.http_client import fetch_page
from scraper.pagination import scrape_paginated
from scraper.service import scrape_item
from utils.logger import get_logger

logger = get_logger(__name__)


def scrape_job(pUrl, pConfig):
    """
    Scrape une offre d'emploi depuis une URL.
    """
    rJob = scrape_item(
        pUrl,
        pConfig,
        fetch_page,
        parse_html,
        extract_job
    )
    return rJob


def scrape_jobs(pUrl, pConfig):
    """
    Scrape plusieurs offres d'emploi.
    """
    logger.info(
        "Début du scraping des offres : %s",
        pUrl
    )

    vResult = scrape_paginated(
        pUrl,
        pConfig,
        fetch_page,
        parse_html,
        extract_jobs,
        extract_next_url,
        "url"
    )

    logger.info(
        "Scraping terminé : %s offre(s) trouvée(s) sur %s page(s)",
        len(vResult.items),
        vResult.page_count
    )

    rResult = vResult
    return rResult