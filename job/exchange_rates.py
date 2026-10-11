"""Taux de change de la Banque centrale européenne, gratuits et sans clé

Les taux servent à estimer un équivalent en euros des salaires en dollars ou en
livres : le résultat est indicatif et signalé comme tel à l'affichage.
"""

import json
import re
from datetime import datetime, timedelta

import requests

from storage.settings_repository import get_setting_values, save_setting_values
from utils.api_client import DEFAULT_TIMEOUT, check_announced_size, read_limited_content
from utils.logger import get_logger
from utils.security import validate_url

logger = get_logger(__name__)

ECB_RATES_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"

RATES_KEY = "exchange_rates"

# Des taux d'une semaine suffisent pour une estimation de salaire.
RATES_MAX_AGE = timedelta(days=7)

# Le fichier de la BCE pèse quelques kilo-octets.
MAX_RATES_SIZE = 64 * 1024

# Une ligne par devise : <Cube currency='USD' rate='1.0812'/>
RATE_PATTERN = re.compile(r"currency=['\"]([A-Z]{3})['\"]\s+rate=['\"]([\d.]+)['\"]")
DATE_PATTERN = re.compile(r"time=['\"](\d{4}-\d{2}-\d{2})['\"]")


def parse_ecb_rates(pText):
    """Lit les taux du fichier de la BCE : unités de devise pour un euro."""

    rRates = {
        vCurrency: float(vRate) for vCurrency, vRate in RATE_PATTERN.findall(pText)
    }

    if not rRates:
        raise ValueError("Aucun taux trouvé dans le fichier de la BCE.")

    rRates["EUR"] = 1.0

    return rRates


def fetch_ecb_rates():
    """Télécharge les taux du jour ; retourne (taux, date de publication)."""

    validate_url(ECB_RATES_URL)

    vResponse = requests.get(
        ECB_RATES_URL, timeout=DEFAULT_TIMEOUT, allow_redirects=False, stream=True
    )

    try:
        vResponse.raise_for_status()
        check_announced_size(vResponse, MAX_RATES_SIZE)
        vText = read_limited_content(vResponse, MAX_RATES_SIZE).decode("utf-8")

    finally:
        vResponse.close()

    vDate = DATE_PATTERN.search(vText)

    rResult = (parse_ecb_rates(vText), vDate.group(1) if vDate else None)

    return rResult


def load_stored_rates(pDatabaseFile):
    """Retourne les taux enregistrés et leur date de récupération, ou ({}, None)."""

    rStored = ({}, None)

    vValue = get_setting_values(pDatabaseFile).get(RATES_KEY)

    if vValue:
        try:
            vData = json.loads(vValue)
            rStored = (vData["rates"], datetime.fromisoformat(vData["fetched_at"]))

        except (ValueError, KeyError, TypeError):
            logger.warning("Taux de change enregistrés illisibles, ignorés")

    return rStored


def get_exchange_rates(pDatabaseFile, pNow):
    """Retourne les taux de change, rafraîchis s'ils datent de plus d'une semaine.

    Sans réseau, les derniers taux connus servent, même anciens ; sans aucun
    taux, les salaires en devises restent simplement sans équivalent en euros.
    """

    rRates, vFetchedAt = load_stored_rates(pDatabaseFile)

    if vFetchedAt is None or pNow - vFetchedAt > RATES_MAX_AGE:
        try:
            vRates, vPublishedOn = fetch_ecb_rates()

        # Toute erreur est tolérée : sans taux à jour, les offres sont enregistrées
        # quand même, avec les derniers taux connus.
        except Exception as vError:  # pylint: disable=broad-exception-caught
            logger.warning("Taux de change de la BCE indisponibles : %s", vError)

        else:
            save_setting_values(
                pDatabaseFile,
                {
                    RATES_KEY: json.dumps(
                        {
                            "rates": vRates,
                            "published_on": vPublishedOn,
                            "fetched_at": pNow.isoformat(),
                        }
                    )
                },
            )
            rRates = vRates

            logger.info(
                "Taux de change de la BCE mis à jour (%s devises, publiés le %s)",
                len(vRates),
                vPublishedOn,
            )

    return rRates
