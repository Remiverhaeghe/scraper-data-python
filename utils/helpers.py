"""
Méthodes utilitaires générales.
"""


def extract_text(soup, selector):
    """Extrait le texte d'un élément HTML."""

    element = soup.select_one(selector)

    if element is None:
        return ""

    return element.get_text(strip=True)