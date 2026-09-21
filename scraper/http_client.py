# ============================================================================
# Gestion des requêtes HTTP du scraper
# ============================================================================


import time

import requests

from scraper.config import ScrapingConfig
from utils.logger import get_logger
from utils.security import validate_url


logger = get_logger(__name__)


MAX_REDIRECTS = 5
CHUNK_SIZE = 64 * 1024


def fetch_page(pUrl, pConfig: ScrapingConfig):
    """
    Récupère le contenu HTML d'une page web.

    :param pUrl: URL de la page à récupérer.
    :param pConfig: Configuration du scraping.
    :return: Contenu HTML.
    """

    logger.info(
        "Récupération de la page : %s",
        pUrl
    )

    vCurrentUrl = pUrl
    vRedirectCount = 0
    vRequestCount = 0
    vResponse = None

    while vCurrentUrl:
        validate_url(
            vCurrentUrl
        )

        # Applique le délai entre deux requêtes HTTP.
        if vRequestCount > 0 and pConfig.delay > 0:
            time.sleep(
                pConfig.delay
            )

        vResponse = _request(
            vCurrentUrl,
            pConfig
        )

        vRequestCount += 1

        if not vResponse.is_redirect:
            break

        vRedirectCount += 1

        if vRedirectCount > MAX_REDIRECTS:
            raise ValueError(
                "Nombre maximum de redirections dépassé."
            )

        vCurrentUrl = vResponse.headers.get(
            "Location"
        )

        if not vCurrentUrl:
            raise ValueError(
                "La redirection ne contient pas de destination."
            )

        logger.info(
            "Redirection détectée vers : %s",
            vCurrentUrl
        )

    vResponse.raise_for_status()

    _validate_response_size(
        vResponse,
        pConfig
    )

    vContent = _read_response_content(
        vResponse,
        pConfig
    )

    vResponse.encoding = vResponse.apparent_encoding

    logger.info(
        "Page récupérée avec succès : %s",
        vCurrentUrl
    )

    rHtml = vContent.decode(
        vResponse.encoding or "utf-8",
        errors="replace"
    )

    return rHtml


def _request(pUrl, pConfig: ScrapingConfig):
    """
    Effectue une requête HTTP avec gestion des nouvelles tentatives.

    :param pUrl: URL à récupérer.
    :param pConfig: Configuration du scraping.
    :return: Réponse HTTP.
    """

    vAttempt = 0
    vResponse = None

    while vResponse is None:
        try:
            vResponse = requests.get(
                pUrl,
                timeout=pConfig.timeout,
                allow_redirects=False,
                stream=True
            )
        except requests.RequestException:
            vAttempt += 1

            if vAttempt > pConfig.retry_count:
                logger.exception(
                    "Échec de récupération après %s tentative(s) : %s",
                    vAttempt,
                    pUrl
                )
                raise

            logger.warning(
                "Échec de récupération, nouvelle tentative "
                "%s/%s : %s",
                vAttempt,
                pConfig.retry_count,
                pUrl
            )

            if pConfig.retry_delay > 0:
                time.sleep(
                    pConfig.retry_delay
                )

    rResponse = vResponse
    return rResponse


def _validate_response_size(
    pResponse,
    pConfig: ScrapingConfig
):
    """
    Vérifie que la taille annoncée de la réponse HTTP respecte la limite.

    :param pResponse: Réponse HTTP.
    :param pConfig: Configuration du scraping.
    """

    vContentLength = pResponse.headers.get(
        "Content-Length"
    )

    if (
        vContentLength is not None
        and int(vContentLength) > pConfig.max_response_size
    ):
        raise ValueError(
            "La taille de la réponse HTTP dépasse la limite autorisée."
        )


def _read_response_content(
    pResponse,
    pConfig: ScrapingConfig
) -> bytes:
    """
    Lit le contenu HTTP par morceaux en contrôlant sa taille réelle.

    :param pResponse: Réponse HTTP.
    :param pConfig: Configuration du scraping.
    :return: Contenu de la réponse en octets.
    """

    vContent = bytearray()
    vContentSize = 0

    for vChunk in pResponse.iter_content(
        chunk_size=CHUNK_SIZE
    ):
        if not vChunk:
            continue

        vContentSize += len(vChunk)

        if vContentSize > pConfig.max_response_size:
            raise ValueError(
                "La taille de la réponse HTTP dépasse la limite autorisée."
            )

        vContent.extend(
            vChunk
        )

    rContent = bytes(
        vContent
    )

    return rContent