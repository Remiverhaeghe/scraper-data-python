"""Client HTTP de l'API publique des tableaux d'offres Ashby"""

from urllib.parse import quote

from utils.api_client import request_json

API_URL = "https://api.ashbyhq.com/posting-api/job-board/{company}"


def get_jobs(pCompany):
    """Retourne toutes les offres publiées par une entreprise sur Ashby."""

    # Dépannage : 404 signale un identifiant inconnu, à lire dans l'adresse
    # jobs.ashbyhq.com/<identifiant> de la page carrière de l'entreprise.
    vData = request_json(
        "GET",
        API_URL.format(company=quote(pCompany)),
        pParams={"includeCompensation": "true"},
    )

    rJobs = vData.get("jobs") or []

    return rJobs
