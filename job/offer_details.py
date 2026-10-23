"""Description lue à l'ouverture d'une offre enregistrée sans elle"""

import requests

from job.sources.smartrecruiters.service import (
    fetch_description as fetch_smartrecruiters_description,
)
from job.sources.workday.service import (
    fetch_description as fetch_workday_description,
)
from storage.job_offers import save_offer_description
from utils.logger import get_logger

logger = get_logger(__name__)

# Sources dont la description n'est lue que pour une partie des offres
DESCRIPTION_FETCHERS = {
    "smartrecruiters": fetch_smartrecruiters_description,
    "workday": fetch_workday_description,
}


def can_fetch_description(pOffer):
    """Indique si la description manquante d'une offre peut être lue à la source."""

    rPossible = bool(
        pOffer
        and not pOffer.get("description")
        and pOffer.get("source") in DESCRIPTION_FETCHERS
    )

    return rPossible


def fetch_missing_description(pDatabaseFile, pOffer):
    """Lit et enregistre la description manquante ; retourne l'offre complétée.

    Une source injoignable ou une offre retirée laisse l'offre telle quelle : la
    fiche s'affiche quand même, sans description.
    """

    if not can_fetch_description(pOffer):
        return pOffer

    try:
        vResult = DESCRIPTION_FETCHERS[pOffer["source"]](pOffer)

    except (requests.RequestException, ValueError) as vException:
        logger.warning(
            "Description de l'offre %s/%s indisponible : %s",
            pOffer["source"],
            pOffer["source_id"],
            vException,
        )
        return pOffer

    if vResult is None or not vResult[0]:
        return pOffer

    vDescription, vUrl = vResult
    save_offer_description(
        pDatabaseFile, pOffer["source"], pOffer["source_id"], vDescription, vUrl
    )
    logger.info(
        "Description lue à l'ouverture : %s/%s", pOffer["source"], pOffer["source_id"]
    )

    rOffer = {**pOffer, "description": vDescription, "url": vUrl}

    return rOffer
