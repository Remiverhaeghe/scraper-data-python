# ============================================================================
# Validation de sécurité des URLs
# ============================================================================


import ipaddress
import socket
from urllib.parse import urlparse


ALLOWED_SCHEMES = {"http", "https"}


def validate_url(pUrl):
    """
    Vérifie qu'une URL peut être utilisée par le scraper.
    """

    if not pUrl:
        raise ValueError("L'URL ne peut pas être vide.")

    vParsedUrl = urlparse(pUrl)

    if vParsedUrl.scheme.lower() not in ALLOWED_SCHEMES:
        raise ValueError("Le schéma de l'URL n'est pas autorisé.")

    if not vParsedUrl.hostname:
        raise ValueError("L'URL ne contient pas de destination valide.")

    try:
        vIpAddress = ipaddress.ip_address(vParsedUrl.hostname)
    except ValueError:
        vIpAddress = None

    if vIpAddress is not None and (
        vIpAddress.is_private
        or vIpAddress.is_loopback
        or vIpAddress.is_link_local
        or vIpAddress.is_multicast
        or vIpAddress.is_reserved
    ):
        raise ValueError("La destination réseau n'est pas autorisée.")

    if vParsedUrl.hostname.lower() == "localhost":
        raise ValueError("La destination localhost n'est pas autorisée.")

    try:
        vAddresses = socket.getaddrinfo(
            vParsedUrl.hostname,
            None
        )
    except socket.gaierror:
        raise ValueError(
            "Impossible de résoudre le nom de domaine."
        )

    for vAddress in vAddresses:
        vIpAddress = ipaddress.ip_address(vAddress[4][0])

        if (
            vIpAddress.is_private
            or vIpAddress.is_loopback
            or vIpAddress.is_link_local
            or vIpAddress.is_multicast
            or vIpAddress.is_reserved
        ):
            raise ValueError(
                "La destination réseau n'est pas autorisée."
            )

    rValid = True
    return rValid