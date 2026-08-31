"""
Service de scraping.
"""

from scraper.http_client import fetch_page
from scraper.parser import extract_job, parse_html


def scrape_job(url):
    """Récupère et analyse une offre."""

    html = fetch_page(url)
    soup = parse_html(html)

    return extract_job(soup)