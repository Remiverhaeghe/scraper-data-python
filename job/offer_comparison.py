"""Comparaison de quelques offres côte à côte, partagée entre le bureau et le web"""

from job.freshness import compute_freshness
from job.preparation import match_offer
from job.presentation import (
    STATUS_LABELS,
    clean_missing_values,
    format_net_salary,
    get_source_label,
)
from job.profile import load_profile
from storage.job_applications import get_application
from storage.job_offers import get_offer
from storage.settings_repository import load_json_setting, save_json_setting
from utils.logger import get_logger

logger = get_logger(__name__)

COMPARISON_KEY = "offer_comparison"

# Au-delà, les colonnes deviennent trop étroites pour être lues
MAX_COMPARED_OFFERS = 3


def load_comparison_keys(pDatabaseFile):
    """Retourne les offres à comparer, en couples (source, identifiant)."""

    rKeys = [
        (vKey[0], str(vKey[1]))
        for vKey in load_json_setting(pDatabaseFile, COMPARISON_KEY, [], list)
        if isinstance(vKey, list) and len(vKey) == 2
    ]

    return rKeys


def toggle_comparison(pDatabaseFile, pSource, pSourceId):
    """Ajoute l'offre à la comparaison, ou l'en retire ; retourne True si elle y est.

    Au-delà de trois offres, la plus ancienne ajoutée laisse sa place.
    """

    vKey = (pSource, str(pSourceId))
    vKeys = load_comparison_keys(pDatabaseFile)

    rAdded = vKey not in vKeys

    vKeys = (
        [*vKeys, vKey][-MAX_COMPARED_OFFERS:]
        if rAdded
        else [vItem for vItem in vKeys if vItem != vKey]
    )

    save_json_setting(pDatabaseFile, COMPARISON_KEY, [list(vItem) for vItem in vKeys])

    logger.info(
        "Offre %s la comparaison : %s %s",
        "ajoutée à" if rAdded else "retirée de",
        pSource,
        pSourceId,
    )

    return rAdded


def clear_comparison(pDatabaseFile):
    """Vide la comparaison."""

    save_json_setting(pDatabaseFile, COMPARISON_KEY, [])


def describe_remote(pOffer):
    """Décrit le télétravail d'une offre."""

    if pOffer.get("remote_days"):
        rText = f"{pOffer['remote_days']} jour(s) par semaine"
    elif pOffer.get("remote") in (1, True, "1", "true", "yes"):
        rText = "Oui"
    else:
        rText = "Non précisé"

    return rText


def build_comparison(pDatabaseFile, pNow):
    """Retourne les offres comparées et une ligne par critère, une valeur par offre."""

    vProfile = load_profile(pDatabaseFile)
    vOffers = []

    for vSource, vSourceId in load_comparison_keys(pDatabaseFile):
        vOffer = get_offer(pDatabaseFile, vSource, vSourceId)

        # Une offre supprimée depuis, par une purge par exemple, est ignorée.
        if vOffer is None:
            continue

        vOffer = clean_missing_values(vOffer)
        vMatch = match_offer(vProfile, vOffer)
        vApplication = get_application(pDatabaseFile, vSource, vSourceId)

        vOffer["comparison"] = {
            "Entreprise": vOffer.get("company") or "Non communiquée",
            "Lieu": vOffer.get("location") or "Non précisé",
            "Distance": (
                f"{round(vOffer['distance_km'])} km"
                if vOffer.get("distance_km") is not None
                else "Inconnue"
            ),
            "Contrat": vOffer.get("contract") or "Non précisé",
            "Net mensuel": format_net_salary(vOffer) or "Non communiqué",
            "Télétravail": describe_remote(vOffer),
            "Correspondance": (
                f"{vMatch['score']} %" if vMatch["score"] is not None else "Inconnue"
            ),
            "Compétences manquantes": ", ".join(vMatch["missing"]) or "Aucune",
            "Fraîcheur": f"{compute_freshness(vOffer, pNow)} / 100",
            "Source": get_source_label(vSource),
            "Suivi": (
                STATUS_LABELS.get(vApplication["status"], vApplication["status"])
                if vApplication
                else "Aucun"
            ),
        }
        vOffers.append(vOffer)

    vLabels = list(vOffers[0]["comparison"]) if vOffers else []

    rComparison = {
        "offers": vOffers,
        "rows": [
            (vLabel, [vOffer["comparison"][vLabel] for vOffer in vOffers])
            for vLabel in vLabels
        ],
    }

    return rComparison
