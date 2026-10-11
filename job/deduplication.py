"""Repérage des offres publiées sur plusieurs sources et de leurs différences"""

from job.fingerprint import normalize
from storage.duplicates import get_decisions
from storage.job_offers import get_offers

# Champs comparés entre les annonces d'un même groupe, avec leur libellé
COMPARED_FIELDS = (
    ("contract", "Contrat"),
    ("net_salary", "Net mensuel"),
    ("location", "Lieu"),
    ("remote", "Télétravail"),
)

MERGED = "merged"
SEPARATE = "separate"


def find_differences(pOffers):
    """Retourne les libellés des champs dont la valeur diffère entre les annonces."""

    rDifferences = []

    for vField, vLabel in COMPARED_FIELDS:
        vValues = {
            normalize(vOffer.get(vField))
            for vOffer in pOffers
            if vOffer.get(vField) not in (None, "")
        }

        if len(vValues) > 1:
            rDifferences.append(vLabel)

    return rDifferences


def group_offers(pOffers, pDecisions):
    """Regroupe les offres de même empreinte en une seule, sauf avis contraire.

    pOffers est trié du plus récent au plus ancien : la première offre d'un
    groupe le représente. Une offre représentante reçoit la liste de ses
    doublons, de ses sources et des différences repérées entre annonces.
    """

    vGroups = {}
    vOrder = []

    for vOffer in pOffers:
        vFingerprint = vOffer.get("fingerprint")
        vKey = (
            vFingerprint
            if vFingerprint and pDecisions.get(vFingerprint) != SEPARATE
            else id(vOffer)
        )

        if vKey not in vGroups:
            vGroups[vKey] = []
            vOrder.append(vKey)

        vGroups[vKey].append(vOffer)

    rOffers = []

    for vKey in vOrder:
        vRepresentative, *vDuplicates = vGroups[vKey]
        vDifferences = find_differences(vGroups[vKey]) if vDuplicates else []

        vRepresentative["duplicates"] = vDuplicates
        vRepresentative["source_labels"] = list(
            dict.fromkeys(vOffer["source_label"] for vOffer in vGroups[vKey])
        )
        vRepresentative["differences"] = vDifferences
        vRepresentative["needs_review"] = bool(vDifferences) and (
            pDecisions.get(vRepresentative.get("fingerprint")) != MERGED
        )

        rOffers.append(vRepresentative)

    return rOffers


def get_offer_group(pDatabaseFile, pOffer, pPrepare):
    """Retourne les annonces d'une offre, leurs différences et la décision prise.

    pPrepare met en forme chaque annonce, comme dans les listes (prepare_offer).
    """

    vFingerprint = pOffer.get("fingerprint")
    vOffers = [pOffer]

    if vFingerprint:
        vOffers = [
            pPrepare(vOffer)
            for vOffer in get_offers(pDatabaseFile, pFingerprint=vFingerprint).to_dict(
                "records"
            )
        ]

    rGroup = {
        "offers": vOffers,
        "differences": find_differences(vOffers) if len(vOffers) > 1 else [],
        "decision": get_decisions(pDatabaseFile).get(vFingerprint),
    }

    return rGroup
