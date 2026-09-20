# ============================================================================
# Gestion des requêtes HTTP du scraper
# ============================================================================


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

    logger.info("Récupération de la page : %s", pUrl)

    vCurrentUrl = pUrl
    vRedirectCount = 0
    vResponse = None

    while vCurrentUrl:
        validate_url(vCurrentUrl)

        try:
            vResponse = requests.get(
                vCurrentUrl,
                timeout=pConfig.timeout,
                allow_redirects=False,
                stream=True
            )
        except requests.RequestException:
            logger.exception(
                "Échec de récupération : %s",
                vCurrentUrl
            )
            raise

        if not vResponse.is_redirect:
            break

        vRedirectCount += 1

        if vRedirectCount > MAX_REDIRECTS:
            raise ValueError(
                "Nombre maximum de redirections dépassé."
            )

        vCurrentUrl = vResponse.headers.get("Location")

        if not vCurrentUrl:
            raise ValueError(
                "La redirection ne contient pas de destination."
            )

        logger.info(
            "Redirection détectée vers : %s",
            vCurrentUrl
        )

    vResponse.raise_for_status()

    _validate_response_size(vResponse, pConfig)

    vContent = _read_response_content(vResponse, pConfig)

    vResponse.encoding = vResponse.apparent_encoding

    logger.info("Page récupérée avec succès : %s", vCurrentUrl)

    rHtml = vContent.decode(
        vResponse.encoding or "utf-8",
        errors="replace"
    )
    return rHtml


def _validate_response_size(pResponse, pConfig: ScrapingConfig):
    """
    Vérifie que la taille annoncée de la réponse HTTP respecte la limite.

    :param pResponse: Réponse HTTP.
    :param pConfig: Configuration du scraping.
    """

    vContentLength = pResponse.headers.get("Content-Length")

    if (
        vContentLength is not None
        and int(vContentLength) > pConfig.max_response_size
    ):
        raise ValueError(
            "La taille de la réponse HTTP dépasse la limite autorisée."
        )


def _read_response_content(pResponse, pConfig: ScrapingConfig) -> bytes:
    """
    Lit le contenu HTTP par morceaux en contrôlant sa taille réelle.

    :param pResponse: Réponse HTTP.
    :param pConfig: Configuration du scraping.
    :return: Contenu de la réponse en octets.
    """

    vContent = bytearray()
    vContentSize = 0

    for vChunk in pResponse.iter_content(chunk_size=CHUNK_SIZE):
        if not vChunk:
            continue

        vContentSize += len(vChunk)

        if vContentSize > pConfig.max_response_size:
            raise ValueError(
                "La taille de la réponse HTTP dépasse la limite autorisée."
            )

        vContent.extend(vChunk)

    rContent = bytes(vContent)
    return rContent