# ============================================================================
# Analyse et extraction des données HTML des offres d'emploi
# ============================================================================


import pandas as pd
from bs4 import BeautifulSoup

from utils.helpers import extract_text
from utils.logger import get_logger


logger = get_logger(__name__)


def parse_html(pHtml):
    """
    Analyse le contenu HTML d'une page.

    :param pHtml: Contenu HTML de la page.
    :return: Document HTML analysé.
    """

    rSoup = BeautifulSoup(
        pHtml,
        "html.parser"
    )

    return rSoup


def extract_job(pSoup):
    """
    Extrait les données d'une offre d'emploi.

    :param pSoup: Élément HTML contenant l'offre.
    :return: Dictionnaire contenant les données extraites.
    """

    logger.info(
        "Extraction d'une offre d'emploi"
    )

    vLink = pSoup.select_one(
        "a"
    )

    vJob = {
        "title": extract_text(
            pSoup,
            "h1"
        ),
        "company": extract_text(
            pSoup,
            ".company"
        ),
        "location": extract_text(
            pSoup,
            ".location"
        ),
        "city": "",
        "postal_code": "",
        "distance_km": None,
        "contract": extract_text(
            pSoup,
            ".contract"
        ),
        "salary_min": None,
        "salary_max": None,
        "salary_period": None,
        "remote": None,
        "remote_days": None,
        "remote_type": None,
        "nearest_metro": None,
        "metro_distance_km": None,
        "date": extract_text(
            pSoup,
            ".date"
        ),
        "url": (
            vLink.get(
                "href",
                ""
            )
            if vLink
            else ""
        ),
        "description": "",
        "missions": "",
        "requirements": "",
        "education": "",
        "skills": ""
    }

    logger.info(
        "Offre extraite : %s",
        vJob["title"]
    )

    rJob = vJob

    return rJob


def extract_jobs(pSoup, pCurrentUrl):
    """
    Extrait plusieurs offres depuis une page HTML.

    :param pSoup: Document HTML analysé.
    :param pCurrentUrl: URL de la page courante.
    :return: DataFrame contenant les offres extraites.
    """

    vJobElements = pSoup.select(
        ".job"
    )

    logger.info(
        "%s offre(s) trouvée(s) dans la page",
        len(vJobElements)
    )

    vJobs = [
        extract_job(vJob)
        for vJob in vJobElements
    ]

    rJobs = pd.DataFrame(
        vJobs
    )

    return rJobs


def extract_next_url(pSoup, pCurrentUrl):
    """
    Extrait l'URL de la page suivante.

    :param pSoup: Document HTML de la page courante.
    :param pCurrentUrl: URL de la page suivante.
    :return: URL de la page suivante ou une chaîne vide.
    """

    vNextLink = pSoup.select_one(
        'a[rel="next"]'
    )

    vNextUrl = ""

    if vNextLink:
        vNextUrl = vNextLink.get(
            "href",
            ""
        )

    rNextUrl = vNextUrl

    return rNextUrl