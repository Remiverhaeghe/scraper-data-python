"""Client HTTP de la liste publique des offres Workable"""

from urllib.parse import quote

from utils.api_client import request_json

API_URL = "https://apply.workable.com/api/v1/widget/accounts/{account}"


def get_account(pAccount):
    """Retourne le nom de l'entreprise et ses offres publiées, descriptions comprises."""

    # Dépannage : 404 signale un compte inconnu, à lire dans l'adresse
    # apply.workable.com/<compte> de la page carrière de l'entreprise.
    rData = request_json(
        "GET",
        API_URL.format(account=quote(pAccount, safe="")),
        pParams={"details": "true"},
    )

    return rData
