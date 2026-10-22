"""Client HTTP de l'API publique des offres SmartRecruiters"""

from urllib.parse import quote

import requests

from utils.api_client import request_json
from utils.logger import get_logger

logger = get_logger(__name__)

API_URL = "https://api.smartrecruiters.com/v1/companies/{company}/postings"

# Maximum accepté par l'API pour une page
PAGE_SIZE = 100


def get_postings(pCompany, pCountry, pOffset=0):
    """Retourne une page de la liste des offres d'une entreprise, sans description."""

    vUrl = API_URL.format(company=quote(pCompany))

    # Dépannage : une liste vide pour une entreprise qui recrute signale souvent
    # un identifiant mal orthographié, visible dans jobs.smartrecruiters.com/<id>.
    try:
        rData = request_json(
            "GET",
            vUrl,
            pParams={"limit": PAGE_SIZE, "offset": pOffset, "country": pCountry},
        )
    except requests.RequestException:
        logger.exception(
            "Erreur lors de la récupération SmartRecruiters : %s", pCompany
        )
        raise

    return rData


def get_posting(pCompany, pPostingId):
    """Retourne le détail d'une offre : description et adresse de candidature."""

    vUrl = f"{API_URL.format(company=quote(pCompany))}/{quote(str(pPostingId))}"

    rData = request_json("GET", vUrl)

    return rData
