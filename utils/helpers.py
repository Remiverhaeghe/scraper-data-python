"""Méthodes utilitaires générales"""

import re

from bs4 import BeautifulSoup


def extract_text(pSoup, pSelector):
    """Extrait le texte d'un élément HTML."""

    vElement = pSoup.select_one(pSelector)

    if vElement is None:
        rText = ""

    else:
        rText = vElement.get_text(strip=True)

    return rText


def extract_price(pValue):
    """Convertit un prix textuel en valeur numérique."""

    if not pValue:
        rPrice = 0.0

    else:
        rPrice = float(pValue.replace("£", "").strip())

    return rPrice


def extract_rating(pElement):
    """Convertit une note textuelle en valeur numérique."""

    vRatings = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}

    if pElement is None:
        rRating = 0

    else:
        rRating = 0

        for vValue in pElement.get("class", []):
            if vValue in vRatings:
                rRating = vRatings[vValue]
                break

    return rRating


def html_to_text(pHtml):
    """Convertit un contenu HTML en texte brut."""

    rText = None

    if pHtml:
        rText = BeautifulSoup(pHtml, "html.parser").get_text(" ", strip=True)

        # Certaines sources envoient du HTML échappé (&lt;p&gt;) : le premier
        # passage le décode, le second retire les balises ainsi révélées.
        if re.search(r"<[a-zA-Z/][^>]*>", rText):
            rText = BeautifulSoup(rText, "html.parser").get_text(" ", strip=True)

    return rText
