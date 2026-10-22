"""Client HTTP de l'API publique des offres Lever"""

from urllib.parse import quote

from utils.api_client import request_json

API_URL = "https://api.lever.co/v0/postings/{company}"


def get_postings(pCompany):
    """Retourne toutes les offres publiées par une entreprise sur Lever."""

    # Dépannage : 404 signale un identifiant inconnu, à lire dans l'adresse
    # jobs.lever.co/<identifiant> de la page carrière de l'entreprise.
    rPostings = request_json(
        "GET", API_URL.format(company=quote(pCompany)), pParams={"mode": "json"}
    )

    return rPostings
