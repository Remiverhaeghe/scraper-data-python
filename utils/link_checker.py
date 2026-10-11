"""Vérification de la disponibilité d'une offre à partir de son lien"""

from urllib.parse import urljoin, urlparse

import requests

from utils.logger import get_logger
from utils.security import validate_url

logger = get_logger(__name__)

MAX_REDIRECTS = 5
TIMEOUT = 10

# Réponses qui signalent une page retirée
EXPIRED_STATUSES = (404, 410)

# Certains sites refusent les requêtes sans navigateur identifié.
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; JobBoardPerso/1.0)"}


def is_parent_page(pTarget, pOriginal):
    """Indique si une redirection mène vers une page parente, comme une liste d'offres."""

    vTarget = urlparse(pTarget)
    vOriginal = urlparse(pOriginal)
    vTargetPath = vTarget.path.rstrip("/")
    vOriginalPath = vOriginal.path.rstrip("/")

    rParent = vTarget.netloc == vOriginal.netloc and (
        vTargetPath == "" or vOriginalPath.startswith(vTargetPath + "/")
    )

    return rParent


def check_offer_link(pUrl):
    """Retourne available, expired, ou None si la réponse ne permet pas de conclure.

    Un refus d'accès (403), une erreur du site ou du réseau ne prouvent rien :
    l'offre n'est alors marquée ni disponible ni expirée.
    """

    rAvailability = None
    vUrl = pUrl

    try:
        for _ in range(MAX_REDIRECTS + 1):
            # Chaque destination est validée : une redirection ne peut pas mener
            # vers une adresse du réseau interne.
            validate_url(vUrl)

            vResponse = requests.get(
                vUrl,
                headers=HEADERS,
                timeout=TIMEOUT,
                allow_redirects=False,
                stream=True,
            )
            vResponse.close()

            if not vResponse.is_redirect:
                if vResponse.status_code in EXPIRED_STATUSES:
                    rAvailability = "expired"
                elif 200 <= vResponse.status_code < 300:
                    rAvailability = "available"
                break

            vNextUrl = urljoin(vUrl, vResponse.headers.get("Location", ""))

            if is_parent_page(vNextUrl, pUrl):
                rAvailability = "expired"
                break

            vUrl = vNextUrl

    except (requests.RequestException, ValueError) as vException:
        logger.warning("Vérification du lien impossible : %s", vException)

    logger.info("Vérification du lien d'une offre : %s", rAvailability or "indéterminé")

    return rAvailability
