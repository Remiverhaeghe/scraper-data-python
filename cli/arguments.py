"""Gestion des arguments de ligne de commande"""

import argparse

from job.contract import CONTRACT_TYPES
from job.sources.registry import SOURCES


def positive_integer(pValue):
    """Vérifie qu'une valeur est un entier positif."""

    vValue = int(pValue)

    if vValue <= 0:
        raise argparse.ArgumentTypeError("La valeur doit être supérieure à 0.")

    rValue = vValue

    return rValue


def positive_float(pValue):
    """Vérifie qu'une valeur est un nombre positif ou nul."""

    vValue = float(pValue)

    if vValue < 0:
        raise argparse.ArgumentTypeError("La valeur doit être supérieure ou égale à 0.")

    rValue = vValue

    return rValue


def parse_arguments():
    """Analyse les arguments fournis en ligne de commande."""

    vParser = argparse.ArgumentParser(
        description="Recherche d'offres d'emploi multi-sources."
    )

    # Configuration commune
    vParser.add_argument(
        "--max-items",
        type=positive_integer,
        default=None,
        help="Nombre maximum d'éléments à récupérer.",
    )

    vParser.add_argument(
        "--delay",
        type=positive_float,
        default=0.0,
        help="Délai entre deux requêtes HTTP, en secondes.",
    )

    vParser.add_argument(
        "--timeout",
        type=positive_integer,
        default=10,
        help="Temps maximum d'attente d'une requête HTTP, en secondes.",
    )

    vParser.add_argument(
        "--max-pages",
        type=positive_integer,
        default=None,
        help="Nombre maximum de pages interrogées par source.",
    )

    # Critères de recherche des offres
    vParser.add_argument(
        "--keyword", default=None, help="Mot-clé recherché dans les offres."
    )

    vParser.add_argument(
        "--location", default=None, help="Localisation recherchée pour les offres."
    )

    vParser.add_argument(
        "--max-distance-km",
        type=positive_float,
        default=None,
        help="Distance maximale autour de la localisation.",
    )

    vParser.add_argument(
        "--contract",
        type=str.upper,
        choices=CONTRACT_TYPES,
        default=None,
        help="Type de contrat recherché.",
    )

    vParser.add_argument(
        "--min-salary",
        type=positive_float,
        default=None,
        help="Salaire net mensuel minimum recherché, avant impôt.",
    )

    vParser.add_argument(
        "--max-salary",
        type=positive_float,
        default=None,
        help="Salaire net mensuel maximum recherché, avant impôt.",
    )

    vParser.add_argument(
        "--remote",
        action="store_true",
        default=None,
        help="Recherche uniquement des offres en télétravail.",
    )

    vParser.add_argument(
        "--min-remote-days",
        type=positive_integer,
        default=None,
        help="Nombre minimum de jours de télétravail.",
    )

    vParser.add_argument(
        "--metro-required",
        action="store_true",
        default=None,
        help="Recherche uniquement les offres accessibles en métro.",
    )

    vParser.add_argument(
        "--max-metro-distance-km",
        type=positive_float,
        default=None,
        help="Distance maximale jusqu'au métro.",
    )

    vParser.add_argument("--education", default=None, help="Formation recherchée.")

    vParser.add_argument(
        "--skills", nargs="+", default=None, help="Compétences recherchées."
    )

    vParser.add_argument(
        "--missions", nargs="+", default=None, help="Missions recherchées."
    )

    vParser.add_argument(
        "--exclude",
        dest="exclude_keywords",
        nargs="+",
        default=None,
        help="Mots qui excluent une offre lorsqu'ils figurent dans son titre.",
    )

    # Sources d'emploi
    vParser.add_argument(
        "--source",
        dest="sources",
        choices=list(SOURCES),
        action="append",
        default=None,
        help=("Source d'emploi à utiliser. " "L'option peut être répétée."),
    )

    rArguments = vParser.parse_args()

    return rArguments
