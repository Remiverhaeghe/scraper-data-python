# ============================================================================
# Analyse et extraction des données HTML des offres d'emploi
# ============================================================================


from bs4 import BeautifulSoup

from job.model import Job
from utils.helpers import extract_text
from utils.logger import get_logger


logger = get_logger(__name__)


def parse_html(pHtml):
    """
    Transforme le HTML en objet BeautifulSoup.
    """

    rSoup = BeautifulSoup(pHtml, "html.parser")
    return rSoup


def extract_job(pSoup):
    """
    Extrait une offre d'emploi depuis le HTML.
    """

    logger.info("Extraction d'une offre d'emploi")

    vLink = pSoup.select_one("a")
    vJob = Job(
        title=extract_text(pSoup, "h1"),
        company=extract_text(pSoup, ".company"),
        location=extract_text(pSoup, ".location"),
        contract=extract_text(pSoup, ".contract"),
        date=extract_text(pSoup, ".date"),
        url=vLink.get("href", "") if vLink else ""
    )

    logger.info("Offre extraite : %s", vJob.title)

    rJob = vJob
    return rJob


def extract_jobs(pSoup):
    """
    Extrait plusieurs offres depuis une page HTML.
    """

    vJobElements = pSoup.select(".job")
    logger.info(
        "%s offre(s) trouvée(s) dans la page",
        len(vJobElements)
    )

    vJobs = [extract_job(vJob) for vJob in vJobElements]

    rJobs = vJobs
    return rJobs