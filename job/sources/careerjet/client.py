"""Client HTTP de l'API de recherche Careerjet (version 4)"""

import re

import requests

from job.sources.careerjet.config import LOCALE_CODE, USER_AGENT
from utils.api_client import request_json
from utils.logger import get_logger

logger = get_logger(__name__)

API_URL = "https://search.api.careerjet.net/v4/query"

# Maximum accepté par l'API pour une page
PAGE_SIZE = 100

# Réponse d'une clé utilisée depuis une adresse non déclarée :
# « Unauthorized access from IP 192.0.2.1 »
REFUSED_IP_PATTERN = re.compile(r"Unauthorized access from IP ([0-9a-fA-F.:]+)")


def read_refused_ip(pResponse):
    """Retourne l'adresse IP refusée par Careerjet, lue dans sa réponse, ou None."""

    vMatch = (
        REFUSED_IP_PATTERN.search(pResponse.text) if pResponse is not None else None
    )

    rIp = vMatch.group(1) if vMatch else None

    return rIp


def search_jobs(pConfig, pKeyword, pLocation, pPage=1):
    """Retourne une page de résultats de recherche."""

    vParams = {
        "locale_code": LOCALE_CODE,
        "keywords": pKeyword or "",
        "location": pLocation or "",
        "sort": "date",
        "page": pPage,
        "page_size": PAGE_SIZE,
        "user_ip": pConfig.user_ip,
        "user_agent": USER_AGENT,
    }
    vHeaders = {"Referer": pConfig.referer} if pConfig.referer else None

    try:
        # Authentification de base : la clé d'éditeur, sans mot de passe.
        rData = request_json(
            "GET",
            API_URL,
            pParams=vParams,
            pHeaders=vHeaders,
            pAuth=(pConfig.api_key, ""),
        )
    except requests.HTTPError as vError:
        # La clé n'est jamais journalisée, seulement le code de l'erreur.
        logger.error(
            "Careerjet a refusé la recherche : HTTP %s",
            vError.response.status_code if vError.response is not None else "?",
        )

        # La clé n'accepte que les adresses IP déclarées dans le compte éditeur ;
        # une box change d'adresse de temps en temps.
        vIp = read_refused_ip(vError.response)

        if vIp:
            raise ValueError(
                f"adresse IP {vIp} refusée : la déclarer dans le compte éditeur "
                "Careerjet (careerjet.com/partners)"
            ) from vError

        raise

    return rData
