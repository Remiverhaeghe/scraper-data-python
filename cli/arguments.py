"""
Gestion des arguments de ligne de commande.
"""

import argparse


def positive_integer(value):
    """Vérifie qu'une valeur est un entier positif."""

    value = int(value)

    if value <= 0:
        raise argparse.ArgumentTypeError(
            "Le nombre de pages doit être supérieur à 0."
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
        type=float,
        default=None,
        help="Prix maximum des livres."
    )

    parser.add_argument(
        "--min-rating",
        type=int,
        default=None,
        help="Note minimum des livres."
    )

    return parser.parse_args()