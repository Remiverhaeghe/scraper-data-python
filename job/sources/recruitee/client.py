"""Client HTTP de l'API publique des offres Recruitee"""

from urllib.parse import quote

from utils.api_client import request_json

API_URL = "https://{company}.recruitee.com/api/offers/"


def get_offers(pCompany):
    """Retourne toutes les offres publiées par une entreprise sur Recruitee."""

    # Dépannage : 404 signale un identifiant inconnu, à lire dans l'adresse
    # <identifiant>.recruitee.com de la page carrière de l'entreprise.
    vData = request_json("GET", API_URL.format(company=quote(pCompany, safe="")))

    rOffers = vData.get("offers") or []

    return rOffers
