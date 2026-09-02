"""
Méthodes utilitaires pour la gestion des URLs.
"""

from urllib.parse import urljoin


def build_absolute_url(base_url, relative_url):
    """Construit une URL absolue à partir d'une URL de base."""

    if not relative_url:
        return ""

    return urljoin(base_url, relative_url)