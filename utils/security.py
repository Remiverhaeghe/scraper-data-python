"""Validation de sécurité des URLs"""

import ipaddress
import socket
from urllib.parse import urlparse

ALLOWED_SCHEMES = {"http", "https"}


def is_forbidden_address(pIpAddress):
    """Indique si une adresse IP désigne un réseau interne ou réservé."""

    rForbidden = (
        pIpAddress.is_private
        or pIpAddress.is_loopback
        or pIpAddress.is_link_local
        or pIpAddress.is_multicast
        or pIpAddress.is_reserved
    )

    return rForbidden


def validate_url(pUrl):
    """Vérifie qu'une URL peut être utilisée par le scraper."""

    if not pUrl:
        raise ValueError("L'URL ne peut pas être vide.")

    vParsedUrl = urlparse(pUrl)

    # file://, ftp:// ou javascript: sont refusés : seules des pages web publiques
    # sont interrogées.
    if vParsedUrl.scheme.lower() not in ALLOWED_SCHEMES:
        raise ValueError("Le schéma de l'URL n'est pas autorisé.")

    if not vParsedUrl.hostname:
        raise ValueError("L'URL ne contient pas de destination valide.")

    try:
        vIpAddress = ipaddress.ip_address(vParsedUrl.hostname)
    except ValueError:
        vIpAddress = None

    if vIpAddress is not None and is_forbidden_address(vIpAddress):
        raise ValueError("La destination réseau n'est pas autorisée.")

    if vParsedUrl.hostname.lower() == "localhost":
        raise ValueError("La destination localhost n'est pas autorisée.")

    # Un nom de domaine peut pointer vers une adresse interne : chaque adresse
    # résolue est vérifiée, pas seulement le nom (protection contre le SSRF).
    try:
        vAddresses = socket.getaddrinfo(vParsedUrl.hostname, None)
    except socket.gaierror:
        raise ValueError("Impossible de résoudre le nom de domaine.") from None

    for vAddress in vAddresses:
        vIpAddress = ipaddress.ip_address(vAddress[4][0])

        if is_forbidden_address(vIpAddress):
            raise ValueError("La destination réseau n'est pas autorisée.")

    rValid = True
    return rValid
