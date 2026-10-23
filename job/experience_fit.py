"""Expérience demandée par une offre, comparée à celle du candidat"""

import re

from job.fingerprint import normalize

# Années que représente un niveau donné en toutes lettres par la source ou
# repéré dans l'annonce (job/enrichment.py)
LEVEL_YEARS = {
    "debutant": 0,
    "entry level": 0,
    "internship": 0,
    "junior": 0,
    "confirme": 3,
    "mid level": 3,
    "mid senior level": 5,
    "senior": 5,
}

YEARS_PATTERN = re.compile(r"(\d{1,2})\s*ans")

# Marge tolérée : une offre qui demande un an de plus reste à portée.
YEARS_MARGIN = 1


def read_required_years(pLevel):
    """Retourne les années d'expérience demandées par une offre, ou None."""

    vMatch = YEARS_PATTERN.search(str(pLevel or ""))

    rYears = int(vMatch.group(1)) if vMatch else LEVEL_YEARS.get(normalize(pLevel))

    return rYears


def is_above_experience(pOffer, pYears):
    """Indique si l'offre demande nettement plus que l'expérience du candidat."""

    vRequired = read_required_years(pOffer.get("experience_level"))

    rAbove = (
        bool(pYears) and vRequired is not None and vRequired > pYears + YEARS_MARGIN
    )

    return rAbove


def describe_experience_fit(pOffer, pYears):
    """Retourne l'expérience demandée comparée à celle du candidat, ou un texte vide."""

    vRequired = read_required_years(pOffer.get("experience_level"))

    if not pYears or vRequired is None:
        return ""

    if vRequired > pYears + YEARS_MARGIN:
        rText = f"demande environ {vRequired} ans, au-dessus de vos {pYears} ans"
    else:
        rText = f"à votre portée ({pYears} ans d'expérience)"

    return rText


def mark_experience_fit(pOffers, pYears):
    """Signale par above_experience les offres qui demandent plus que le candidat."""

    for vOffer in pOffers:
        vOffer["above_experience"] = is_above_experience(vOffer, pYears)
        vOffer["required_years"] = read_required_years(vOffer.get("experience_level"))
