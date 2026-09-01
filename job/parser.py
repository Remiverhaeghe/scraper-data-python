"""
Analyse du contenu HTML.
"""

from bs4 import BeautifulSoup

from job.model import Job
from utils.helpers import extract_rating, extract_text








"""
Analyse du contenu HTML.
"""

from bs4 import BeautifulSoup

from job.model import Job
from utils.helpers import extract_text


def parse_html(html):
    """Transforme le HTML en objet BeautifulSoup."""

    return BeautifulSoup(html, "html.parser")


def extract_job(soup):
    """Extrait une offre d'emploi depuis le HTML."""

    link = soup.select_one("a")

    return Job(
        title=extract_text(soup, "h1"),
        company=extract_text(soup, ".company"),
        location=extract_text(soup, ".location"),
        contract=extract_text(soup, ".contract"),
        date=extract_text(soup, ".date"),
        url=link.get("href", "") if link else ""
    )

def extract_jobs(soup):
    """Extrait plusieurs offres depuis une page HTML."""

    job_elements = soup.select(".job")

    return [extract_job(job) for job in job_elements]
