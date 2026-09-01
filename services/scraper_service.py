"""
Service de scraping.
"""

from scraper.http_client import fetch_page
from scraper.parser import extract_job, extract_jobs, parse_html
from utils.logger import get_logger

logger = get_logger(__name__)

def scrape_job(url):
    """Récupère et analyse une offre."""

    logger.info("Début du scraping : %s", url)

    html = fetch_page(url)
    soup = parse_html(html)

    job = extract_job(soup)

    logger.info("Scraping terminé : %s", url)

    return job


def scrape_jobs(url):
    """Récupère et analyse plusieurs offres."""

    logger.info("Début du scraping : %s", url)

    html = fetch_page(url)
    soup = parse_html(html)

    jobs = extract_jobs(soup)

    logger.info("Scraping terminé : %s offre(s) trouvée(s)", len(jobs))

    return jobs