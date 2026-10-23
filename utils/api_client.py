"""Appels sécurisés aux API JSON des sources d'offres"""

import json
import time
from urllib.parse import urlparse

import requests

from config import MAX_RESPONSE_SIZE_MB
from utils.logger import get_logger
from utils.security import validate_url

logger = get_logger(__name__)

CHUNK_SIZE = 64 * 1024

DEFAULT_TIMEOUT = 10

MAX_RESPONSE_SIZE = int(MAX_RESPONSE_SIZE_MB * 1024 * 1024)

# Début du corps gardé pour une réponse en erreur : assez pour son message
ERROR_BODY_SIZE = 2048

# Trop de demandes (429) ou service saturé (503) : nouvel essai après le délai
# demandé par le serveur, borné, faute de quoi la source échoue comme avant.
RETRY_STATUSES = (429, 503)
MAX_RETRIES = 2
DEFAULT_RETRY_WAIT = 5
MAX_RETRY_WAIT = 30


def read_retry_wait(pResponse):
    """Retourne l'attente demandée par le serveur en secondes, ou None si trop longue."""

    vHeader = pResponse.headers.get("Retry-After", "")

    # Une date HTTP à la place d'un nombre de secondes : attente par défaut.
    vWait = int(vHeader) if vHeader.strip().isdigit() else DEFAULT_RETRY_WAIT

    rWait = max(vWait, 1) if vWait <= MAX_RETRY_WAIT else None

    return rWait


def check_announced_size(pResponse, pMaxSize):
    """Refuse une réponse dont la taille annoncée dépasse la limite."""

    vContentLength = pResponse.headers.get("Content-Length")

    if vContentLength is not None and int(vContentLength) > pMaxSize:
        raise ValueError("La taille de la réponse HTTP dépasse la limite autorisée.")


def read_limited_content(pResponse, pMaxSize):
    """Lit le contenu par morceaux en contrôlant sa taille réelle.

    La taille annoncée peut être absente ou fausse : seule la lecture effective
    garantit qu'une réponse démesurée n'épuise pas la mémoire.
    """

    vContent = bytearray()

    for vChunk in pResponse.iter_content(chunk_size=CHUNK_SIZE):
        vContent.extend(vChunk)

        if len(vContent) > pMaxSize:
            raise ValueError(
                "La taille de la réponse HTTP dépasse la limite autorisée."
            )

    rContent = bytes(vContent)

    return rContent


def request_bytes(
    pMethod,
    pUrl,
    pParams=None,
    pHeaders=None,
    pJson=None,
    pData=None,
    pTimeout=DEFAULT_TIMEOUT,
    pMaxSize=MAX_RESPONSE_SIZE,
    pExpectedType="json",
    pAuth=None,
):
    """Interroge une source et retourne le contenu brut de sa réponse.

    La destination est validée (pas d'adresse interne), les redirections sont
    refusées, la taille de la réponse est plafonnée et son type doit contenir
    pExpectedType (json, xml). Les erreurs HTTP sont levées telles quelles pour
    que chaque source masque ses éventuelles clés avant de les journaliser.
    """

    # Dépannage : une URL refusée ici vise une adresse locale ou privée, bloquée
    # pour qu'une source ne puisse pas faire interroger le réseau interne.
    validate_url(pUrl)

    for vAttempt in range(MAX_RETRIES + 1):
        vResponse = requests.request(
            pMethod,
            pUrl,
            params=pParams,
            headers=pHeaders,
            json=pJson,
            data=pData,
            auth=pAuth,
            timeout=pTimeout,
            # Une redirection pourrait mener vers une adresse non validée : elle
            # est refusée et signalée comme erreur plutôt que suivie.
            allow_redirects=False,
            stream=True,
        )

        vWait = (
            read_retry_wait(vResponse)
            if vResponse.status_code in RETRY_STATUSES and vAttempt < MAX_RETRIES
            else None
        )

        if vWait is None:
            break

        vResponse.close()
        logger.warning(
            "HTTP %s de %s : nouvel essai dans %s s",
            vResponse.status_code,
            # L'hôte seul : certaines API (Jooble) portent la clé dans le chemin.
            urlparse(pUrl).netloc,
            vWait,
        )
        time.sleep(vWait)

    try:
        if vResponse.is_redirect:
            raise ValueError("Redirection refusée : une API ne doit pas rediriger.")

        if vResponse.status_code >= 400:
            # Le début du corps explique souvent le refus (clé, adresse IP) : il
            # reste lisible par la source dans l'erreur, sans être journalisé ici.
            # pylint: disable-next=protected-access
            vResponse._content = next(vResponse.iter_content(ERROR_BODY_SIZE), b"")

        vResponse.raise_for_status()

        vContentType = vResponse.headers.get("Content-Type", "")

        # Une page HTML à la place du contenu attendu signale souvent une
        # maintenance du site ou une clé refusée présentée sous forme de page.
        if pExpectedType not in vContentType.lower():
            raise ValueError(f"Réponse inattendue : type {vContentType or 'inconnu'}")

        check_announced_size(vResponse, pMaxSize)

        rContent = read_limited_content(vResponse, pMaxSize)

    finally:
        vResponse.close()

    return rContent


def request_json(pMethod, pUrl, **pOptions):
    """Interroge une API et retourne sa réponse JSON décodée.

    Mêmes protections que request_bytes ; pOptions reprend ses paramètres.
    """

    # json.loads détecte lui-même l'encodage UTF-8, UTF-16 ou UTF-32 des octets.
    rData = json.loads(request_bytes(pMethod, pUrl, **pOptions))

    return rData
