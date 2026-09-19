# ============================================================================
# Gestion des arguments de ligne de commande
# ============================================================================


import argparse

from config import MIN_RATING, MAX_RATING


def positive_integer(pValue):
    """
    Vérifie qu'une valeur est un entier positif.

    :param pValue: Valeur à vérifier.
    :return: Valeur convertie en entier.
    """

    vValue = int(pValue)

    if vValue <= 0:
        raise argparse.ArgumentTypeError(
            "La valeur doit être supérieure à 0."
        )

    rValue = vValue

    return rValue


def positive_float(pValue):
    """
    Vérifie qu'une valeur est un nombre positif ou nul.

    :param pValue: Valeur à vérifier.
    :return: Valeur convertie en nombre décimal.
    """

    vValue = float(pValue)

    if vValue < 0:
        raise argparse.ArgumentTypeError(
            "La valeur doit être supérieure ou égale à 0."
        )

    rValue = vValue

    return rValue


def valid_rating(pValue):
    """
    Vérifie qu'une note est comprise dans les limites configurées.

    :param pValue: Note à vérifier.
    :return: Note convertie en entier.
    """

    vValue = int(pValue)

    if vValue < MIN_RATING or vValue > MAX_RATING:
        raise argparse.ArgumentTypeError(
            f"La note doit être comprise entre "
            f"{MIN_RATING} et {MAX_RATING}."
        )

    rValue = vValue

    return rValue


def parse_arguments():
    """
    Analyse les arguments fournis en ligne de commande.

    :return: Arguments fournis par l'utilisateur.
    """

    vParser = argparse.ArgumentParser(
        description="Scrape les livres depuis Books to Scrape."
    )

    # Configuration commune
    vParser.add_argument(
        "--max-items",
        type=positive_integer,
        default=None,
        help="Nombre maximum d'éléments à récupérer."
    )

    vParser.add_argument(
        "--delay",
        type=positive_float,
        default=0.0,
        help="Délai entre deux requêtes HTTP, en secondes."
    )

    vParser.add_argument(
        "--timeout",
        type=positive_integer,
        default=10,
        help="Temps maximum d'attente d'une requête HTTP, en secondes."
    )

    # Configuration spécifique aux livres
    vParser.add_argument(
        "--max-pages",
        type=positive_integer,
        default=None,
        help="Nombre maximum de pages à scraper."
    )

    vParser.add_argument(
        "--refresh",
        action="store_true",
        help="Relance le scraping avant d'exploiter les données."
    )

    vParser.add_argument(
        "--title",
        default=None,
        help="Titre ou texte à rechercher dans les livres."
    )

    vParser.add_argument(
        "--max-price",
        type=positive_float,
        default=None,
        help="Prix maximum des livres."
    )

    vParser.add_argument(
        "--min-rating",
        type=valid_rating,
        default=None,
        help="Note minimum des livres."
    )

    rArguments = vParser.parse_args()

    return rArguments