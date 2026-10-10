"""Méthodes utilitaires pour la gestion des URLs"""

from urllib.parse import urljoin


def build_absolute_url(pBaseUrl, pRelativeUrl):
    """Construit une URL absolue à partir d'une URL de base."""

    if not pRelativeUrl:
        rUrl = ""

    else:
        rUrl = urljoin(pBaseUrl, pRelativeUrl)

    return rUrl
