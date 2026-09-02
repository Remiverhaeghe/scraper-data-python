"""
Méthodes utilitaires générales.
"""


def extract_text(soup, selector):
    """Extrait le texte d'un élément HTML."""

    element = soup.select_one(selector)

    if element is None:
        return ""

    return element.get_text(strip=True)


def extract_price(value):
    """Convertit un prix textuel en valeur numérique."""

    if not value:
        return 0.0

    return float(value.replace("£", "").strip())


def extract_rating(element):
    """Convertit une note textuelle en valeur numérique."""

    ratings = {
        "One": 1,
        "Two": 2,
        "Three": 3,
        "Four": 4,
        "Five": 5
    }

    if element is None:
        return 0

    for value in element.get("class", []):
        if value in ratings:
            return ratings[value]

    return 0