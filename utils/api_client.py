"""Appels sécurisés aux API JSON des sources d'offres"""

import json

import requests

from config import MAX_RESPONSE_SIZE_MB
from utils.logger import get_logger
from utils.security import validate_url

logger = get_logger(__name__)

CHUNK_SIZE = 64 * 1024

DEFAULT_TIMEOUT = 10

MAX_RESPONSE_SIZE = int(MAX_RESPONSE_SIZE_MB * 1024 * 1024)


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


def request_json(
    pMethod,
    pUrl,
    pParams=None,
    pHeaders=None,
    pJson=None,
    pData=None,
    pTimeout=DEFAULT_TIMEOUT,
    pMaxSize=MAX_RESPONSE_SIZE,
):
    """Interroge une API et retourne sa réponse JSON décodée.

    La destination est validée (pas d'adresse interne), les redirections sont
    refusées, la taille de la réponse est plafonnée et son type doit être JSON.
    Les erreurs HTTP sont levées telles quelles pour que chaque source masque
    ses éventuelles clés avant de les journaliser.
    """

    # Dépannage : une URL refusée ici vise une adresse locale ou privée, bloquée
    # pour qu'une source ne puisse pas faire interroger le réseau interne.
    validate_url(pUrl)

    vResponse = requests.request(
        pMethod,
        pUrl,
        params=pParams,
        headers=pHeaders,
        json=pJson,
        data=pData,
        timeout=pTimeout,
        # Une redirection pourrait mener vers une adresse non validée : elle est refusée
        # et signalée comme erreur plutôt que suivie.
        allow_redirects=False,
        stream=True,
    )

    try:
        if vResponse.is_redirect:
            raise ValueError("Redirection refusée : une API ne doit pas rediriger.")

        vResponse.raise_for_status()

        vContentType = vResponse.headers.get("Content-Type", "")

        # Une page HTML à la place du JSON signale souvent une maintenance du site ou
        # une clé refusée présentée sous forme de page.
        if "json" not in vContentType.lower():
            raise ValueError(f"Réponse inattendue : type {vContentType or 'inconnu'}")

        check_announced_size(vResponse, pMaxSize)

        vContent = read_limited_content(vResponse, pMaxSize)

    finally:
        vResponse.close()

    # json.loads détecte lui-même l'encodage UTF-8, UTF-16 ou UTF-32 des octets.
    rData = json.loads(vContent)

    return rData
