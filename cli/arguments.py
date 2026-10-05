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
        description="Scraper de données multi-domaines."
    )

    # Domaine à traiter
    vParser.add_argument(
        "--type",
        choices=["book", "job"],
        default="book",
        help="Type de données à scraper."
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

    # Configuration spécifique aux offres d'emploi
    vParser.add_argument(
        "--keyword",
        default=None,
        help="Mot-clé recherché dans les offres."
    )

    vParser.add_argument(
        "--location",
        default=None,
        help="Localisation recherchée pour les offres."
    )

    vParser.add_argument(
        "--max-distance-km",
        type=positive_float,
        default=None,
        help="Distance maximale autour de la localisation."
    )

    vParser.add_argument(
        "--contract",
        default=None,
        help="Type de contrat recherché."
    )

    vParser.add_argument(
        "--min-salary",
        type=positive_float,
        default=None,
        help="Salaire minimum recherché."
    )

    vParser.add_argument(
        "--max-salary",
        type=positive_float,
        default=None,
        help="Salaire maximum recherché."
    )

    vParser.add_argument(
        "--remote",
        action="store_true",
        default=None,
        help="Recherche uniquement des offres en télétravail."
    )

    vParser.add_argument(
        "--min-remote-days",
        type=positive_integer,
        default=None,
        help="Nombre minimum de jours de télétravail."
    )

    vParser.add_argument(
        "--metro-required",
        action="store_true",
        default=None,
        help="Recherche uniquement les offres accessibles en métro."
    )

    vParser.add_argument(
        "--max-metro-distance-km",
        type=positive_float,
        default=None,
        help="Distance maximale jusqu'au métro."
    )

    vParser.add_argument(
        "--education",
        default=None,
        help="Formation recherchée."
    )

    vParser.add_argument(
        "--skills",
        nargs="+",
        default=None,
        help="Compétences recherchées."
    )

    vParser.add_argument(
        "--missions",
        nargs="+",
        default=None,
        help="Missions recherchées."
    )

    # Sources d'emploi
    vParser.add_argument(
        "--source",
        dest="sources",
        choices=[
            "france-travail",
            "greenhouse",
            "lever"
        ],
        action="append",
        default=None,
        help=(
            "Source d'emploi à utiliser. "
            "L'option peut être répétée."
        )
    )

    rArguments = vParser.parse_args()

    return rArguments