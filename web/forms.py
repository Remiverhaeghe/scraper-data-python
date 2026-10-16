"""Lecture des champs de formulaire : montants, durées et dates saisis"""

from datetime import datetime

from job.presentation import PUBLISHED_PERIODS
from utils.logger import get_logger

logger = get_logger(__name__)


# Lecture des filtres saisis : une valeur invalide est ignorée et journalisée,
# jamais transformée en erreur 500.
def parse_amount(pValue):
    """Convertit une saisie de montant en nombre, en ignorant une saisie invalide."""

    rAmount = None

    try:
        rAmount = float(pValue.replace(" ", "").replace(",", ".")) if pValue else None

    except ValueError:
        logger.warning("Montant de filtre ignoré : %s", pValue)

    return rAmount


def parse_published_days(pValue):
    """Convertit la période de publication choisie, en ignorant une valeur inconnue."""

    rDays = None

    if pValue.isdigit() and int(pValue) in PUBLISHED_PERIODS:
        rDays = int(pValue)

    return rDays


def parse_date(pValue, pFormat="%Y-%m-%d"):
    """Convertit une date saisie (AAAA-MM-JJ par défaut), ou retourne None."""

    rDate = None

    try:
        rDate = datetime.strptime(pValue, pFormat) if pValue else None

    except ValueError:
        logger.warning("Date saisie ignorée : %s", pValue)

    return rDate
