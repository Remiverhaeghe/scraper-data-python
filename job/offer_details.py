"""Description lue après coup pour une offre enregistrée sans elle : à son
ouverture, ou par lots en tâche de fond
"""

import requests

from job.sources.smartrecruiters.service import (
    fetch_description as fetch_smartrecruiters_description,
)
from job.sources.workday.service import (
    fetch_description as fetch_workday_description,
)
from storage.job_offers import (
    get_offers_without_description,
    mark_description_unavailable,
    save_offer_description,
)
from utils.logger import get_logger

logger = get_logger(__name__)

# Sources dont la description n'est lue que pour une partie des offres
DESCRIPTION_FETCHERS = {
    "smartrecruiters": fetch_smartrecruiters_description,
    "workday": fetch_workday_description,
}

# Descriptions lues à chaque passage du planificateur, pour rester discret
DESCRIPTION_BATCH = 30


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


def complete_missing_descriptions(pDatabaseFile, _pNow=None, pLimit=DESCRIPTION_BATCH):
    """Lit à la source un lot de descriptions manquantes ; retourne le bilan.

    Une offre retirée est notée indisponible ; une source injoignable arrête le
    passage, repris au suivant. La date n'est pas utilisée : la signature est
    celle des tâches du planificateur.
    """

    rReport = {"read": 0, "unavailable": 0}

    for vOffer in get_offers_without_description(
        pDatabaseFile, tuple(DESCRIPTION_FETCHERS), pLimit
    ):
        try:
            vResult = DESCRIPTION_FETCHERS[vOffer["source"]](vOffer)

        except requests.HTTPError as vException:
            # Serveur en panne ou débit limité : le passage reprendra plus tard.
            if vException.response is None or (
                vException.response.status_code >= 500
                or vException.response.status_code == 429
            ):
                logger.warning("Descriptions interrompues : %s", vException)
                break

            vResult = None

        except ValueError:
            # Réponse propre à cette offre (redirection, contenu inattendu) : elle
            # ne doit pas bloquer les suivantes.
            vResult = None

        except requests.RequestException as vException:
            logger.warning("Descriptions interrompues : %s", vException)
            break

        if vResult is None or not vResult[0]:
            mark_description_unavailable(
                pDatabaseFile, vOffer["source"], vOffer["source_id"]
            )
            rReport["unavailable"] += 1
            continue

        save_offer_description(
            pDatabaseFile, vOffer["source"], vOffer["source_id"], *vResult
        )
        rReport["read"] += 1

    if rReport["read"] or rReport["unavailable"]:
        logger.info(
            "Descriptions complétées : %s lue(s), %s indisponible(s)",
            rReport["read"],
            rReport["unavailable"],
        )

    return rReport
