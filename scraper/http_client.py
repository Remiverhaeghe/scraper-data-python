"""
Gestion des requêtes HTTP du scraper.
"""

import requests


def fetch_page(url):
    """
    Récupère le contenu HTML d'une page web.

    :param url: URL de la page à récupérer.
    :return: Contenu HTML.
    """

    response = requests.get(url)
    response.raise_for_status()

    return response.text