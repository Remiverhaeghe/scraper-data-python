"""Client HTTP de l'API Remote OK"""

from utils.api_client import request_json

API_URL = "https://remoteok.com/api"


def get_jobs():
    """Retourne les offres récentes ; le premier élément, les conditions d'usage, est retiré.

    Conditions de l'API : citer Remote OK et renvoyer vers son offre, ce que fait
    l'application avec le nom de la source et le lien de chaque offre.
    """

    vData = request_json("GET", API_URL)

    rJobs = [vItem for vItem in vData if isinstance(vItem, dict) and vItem.get("id")]

    return rJobs
