# ============================================================================
# Service de scraping des offres d'emploi
# ============================================================================


from job.parser import (
    extract_job,
    extract_jobs,
    parse_html
)
from scraper.http_client import fetch_page
from utils.logger import get_logger


logger = get_logger(__name__)


def scrape_job(pUrl, pConfig):
    """
    Récupère et analyse une offre d'emploi.
    """

    logger.info("Début du scraping : %s", pUrl)

    vHtml = fetch_page(pUrl, pConfig)
    vSoup = parse_html(vHtml)
    vJob = extract_job(vSoup)

    logger.info("Scraping terminé : %s", pUrl)

    rJob = vJob
    return rJob


def scrape_jobs(pUrl, pConfig):
    """
    Récupère et analyse plusieurs offres d'emploi.
    """

    logger.info("Début du scraping : %s", pUrl)

    vHtml = fetch_page(pUrl, pConfig)
    vSoup = parse_html(vHtml)
    vJobs = extract_jobs(vSoup)

    logger.info(
        "Scraping terminé : %s offre(s) trouvée(s)",
        len(vJobs)
    )

    rJobs = vJobs
    return rJobs