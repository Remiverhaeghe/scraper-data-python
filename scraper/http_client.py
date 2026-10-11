"""Gestion des requêtes HTTP du scraper"""

import time

import requests

from scraper.config import ScrapingConfig
from utils.api_client import check_announced_size, read_limited_content
from utils.logger import get_logger
from utils.security import validate_url

logger = get_logger(__name__)


MAX_REDIRECTS = 5


def fetch_page(pUrl, pConfig: ScrapingConfig):
    """Récupère le contenu HTML d'une page web."""

    logger.info("Récupération de la page : %s", pUrl)

    vCurrentUrl = pUrl
    vRedirectCount = 0
    vRequestCount = 0
    vResponse = None

    # Les redirections sont suivies à la main, et non par requests, pour valider
    # chaque destination : une page ne peut pas rediriger vers une adresse interne.
    while vCurrentUrl:
        validate_url(vCurrentUrl)

        # Applique le délai entre deux requêtes HTTP.
        if vRequestCount > 0 and pConfig.delay > 0:
            time.sleep(pConfig.delay)

        vResponse = _request(vCurrentUrl, pConfig)

        vRequestCount += 1

        if not vResponse.is_redirect:
            break

        vRedirectCount += 1

        if vRedirectCount > MAX_REDIRECTS:
            raise ValueError("Nombre maximum de redirections dépassé.")

        vCurrentUrl = vResponse.headers.get("Location")

        if not vCurrentUrl:
            raise ValueError("La redirection ne contient pas de destination.")

        logger.info("Redirection détectée vers : %s", vCurrentUrl)

    vResponse.raise_for_status()

    check_announced_size(vResponse, pConfig.max_response_size)

    # Détermine l'encodage avant de consommer le flux.
    # Des accents illisibles (Ã©) viennent d'un encodage mal annoncé par le site :
    # l'encodage détecté sur le contenu est préféré à celui de l'en-tête.
    vEncoding = vResponse.apparent_encoding

    if vEncoding:
        vResponse.encoding = vEncoding

    vContent = read_limited_content(vResponse, pConfig.max_response_size)

    logger.info("Page récupérée avec succès : %s", vCurrentUrl)

    rHtml = vContent.decode(vEncoding or "utf-8", errors="replace")

    return rHtml


def _request(pUrl, pConfig: ScrapingConfig):
    """Effectue une requête HTTP avec gestion des nouvelles tentatives."""

    vAttempt = 0
    vResponse = None

    while vResponse is None:
        try:
            vResponse = requests.get(
                pUrl, timeout=pConfig.timeout, allow_redirects=False, stream=True
            )

        except requests.RequestException:
            vAttempt += 1

            if vAttempt > pConfig.retry_count:
                logger.exception(
                    "Échec de récupération après %s tentative(s) : %s", vAttempt, pUrl
                )
                raise

            logger.warning(
                "Échec de récupération, nouvelle tentative " "%s/%s : %s",
                vAttempt,
                pConfig.retry_count,
                pUrl,
            )

            if pConfig.retry_delay > 0:
                time.sleep(pConfig.retry_delay)

    rResponse = vResponse

    return rResponse
