"""
Gestion des arguments de ligne de commande.
"""

import argparse

from config import MIN_RATING, MAX_RATING


def positive_integer(value):
    """Vérifie qu'une valeur est un entier positif."""

    value = int(value)

    if value <= 0:
        raise argparse.ArgumentTypeError(
            "Le nombre de pages doit être supérieur à 0."
        )

    return value


def positive_float(value):
    """Vérifie qu'une valeur est un nombre positif."""

    value = float(value)

    if value < 0:
        raise argparse.ArgumentTypeError(
            "Le prix doit être supérieur ou égal à 0."
        )

    return value


def valid_rating(value): 
    """Vérifie qu'une note est comprise dans les limites configurées."""

    value = int(value)

    if value < MIN_RATING or value > MAX_RATING: 
        raise argparse.ArgumentTypeError(
            f"La note doit être comprise entre "
            f"{MIN_RATING} et {MAX_RATING}."
        )

    return value

def parse_arguments():
    """Analyse les arguments fournis en ligne de commande."""

    parser = argparse.ArgumentParser(
        description="Scrape les livres depuis Books to Scrape."
    )

    parser.add_argument(
        "--max-pages",
        type=positive_integer,
        default=None,
        help="Nombre maximum de pages à scraper."
    )

    parser.add_argument(
        "--title", 
        default=None,
        help="Titre ou texte à rechercher dans les livres."
    )

    parser.add_argument(
        "--max-price", 
        type=positive_float,
        default=None,
        help="Prix maximum des livres."
    )

    parser.add_argument(
        "--min-rating",
        type=valid_rating,
        default=None,
        help="Note minimum des livres."
    )

    return parser.parse_args()