# ============================================================================
# Service de scraping des offres d'emploi
# ============================================================================


from job.parser import (
    extract_job,
    extract_jobs,
    extract_next_url,
    parse_html
)
from scraper.http_client import fetch_page
from scraper.pagination import scrape_paginated
from utils.logger import get_logger


logger = get_logger(__name__)


def scrape_job(pUrl, pConfig):
    """
    Scrape une offre d'emploi depuis une URL.

    :param pUrl: URL de l'offre.
    :param pConfig: Configuration du scraping.
    :return: Données de l'offre extraite.
    """

    logger.info(
        "Début du scraping : %s",
        pUrl
    )

    vHtml = fetch_page(
        pUrl,
        pConfig
    )

    vSoup = parse_html(
        vHtml
    )

    vJob = extract_job(
        vSoup
    )

    logger.info(
        "Scraping terminé : %s",
        pUrl
    )

    rJob = vJob

    return rJob


def scrape_jobs(pUrl, pConfig):
    """
    Scrape plusieurs offres d'emploi avec pagination.

    :param pUrl: URL de départ du scraping.
    :param pConfig: Configuration du scraping.
    :return: Résultat du scraping paginé.
    """

    logger.info(
        "Début du scraping : %s",
        pUrl
    )

    rResult = scrape_paginated(
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
        len(rResult.items),
        rResult.page_count
    )

    return rResult