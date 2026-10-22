"""Client HTTP de l'API Working Nomads"""

from utils.api_client import request_json

API_URL = "https://www.workingnomads.com/api/exposed_jobs/"


def get_jobs():
    """Retourne les offres récentes en télétravail."""

    rJobs = request_json("GET", API_URL)

    return rJobs
