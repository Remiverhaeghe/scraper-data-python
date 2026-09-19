# ============================================================================
# Méthodes utilitaires générales
# ============================================================================


def extract_text(pSoup, pSelector):
    """
    Extrait le texte d'un élément HTML.

    :param pSoup: Élément BeautifulSoup dans lequel rechercher.
    :param pSelector: Sélecteur CSS de l'élément à rechercher.
    :return: Texte extrait ou chaîne vide.
    """

    vElement = pSoup.select_one(
        pSelector
    )

    if vElement is None:
        rText = ""

    else:
        rText = vElement.get_text(
            strip=True
        )

    return rText


def extract_price(pValue):
    """
    Convertit un prix textuel en valeur numérique.

    :param pValue: Prix sous forme textuelle.
    :return: Prix sous forme de nombre décimal.
    """

    if not pValue:
        rPrice = 0.0

    else:
        rPrice = float(
            pValue.replace(
                "£",
                ""
            ).strip()
        )

    return rPrice


def extract_rating(pElement):
    """
    Convertit une note textuelle en valeur numérique.

    :param pElement: Élément HTML contenant la classe de notation.
    :return: Note comprise entre 0 et 5.
    """

    vRatings = {
        "One": 1,
        "Two": 2,
        "Three": 3,
        "Four": 4,
        "Five": 5
    }

    if pElement is None:
        rRating = 0

    else:
        rRating = 0

        for vValue in pElement.get(
            "class",
            []
        ):
            if vValue in vRatings:
                rRating = vRatings[vValue]
                break

    return rRating