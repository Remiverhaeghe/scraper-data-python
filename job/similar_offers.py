"""Nouvelles offres proches de celles retenues, comparées par règles

La signature d'une offre réunit ses compétences et les mots significatifs de
son titre ; deux offres se ressemblent d'autant plus qu'elles en partagent
(indice de Jaccard). Seules les compétences enregistrées sont lues : la
détection dans la description serait trop lente pour l'accueil.
"""

from datetime import timedelta

from job.fingerprint import normalize
from job.presentation import to_list
from storage.job_offers import get_offers

# Offres qui servent de référence : celles que l'on a jugées intéressantes
REFERENCE_STATUSES = ("INTERESTED", "APPLIED", "INTERVIEW", "ACCEPTED")

# Offres comparées : découvertes récemment et pas encore suivies
SIMILAR_OFFER_DAYS = 14

# En dessous, la ressemblance tient du hasard d'un mot commun.
MIN_SIMILARITY = 30

# Ressemblance à une offre ignorée qui fait passer une offre en bas de liste :
# plus stricte, pour ne pas écarter une offre pour un mot de titre partagé.
LIKE_IGNORED_SIMILARITY = 60

# Mots de titre trop courants pour distinguer deux postes
TITLE_STOP_WORDS = {
    "and",
    "des",
    "for",
    "les",
    "pour",
    "the",
    "une",
    "cdi",
    "cdd",
    "poste",
    "senior",
    "junior",
    "confirme",
    "confirmee",
}


def build_signature(pOffer):
    """Retourne les compétences et les mots significatifs du titre d'une offre."""

    vWords = {
        vWord
        for vWord in normalize(pOffer.get("title")).split()
        if len(vWord) > 2 and vWord not in TITLE_STOP_WORDS
    }

    rSignature = vWords | {
        f"competence:{normalize(vSkill)}" for vSkill in to_list(pOffer.get("skills"))
    }

    return rSignature


def compute_similarity(pFirst, pSecond):
    """Retourne la part d'éléments communs à deux signatures, sur 100."""

    vUnion = pFirst | pSecond

    rSimilarity = round(100 * len(pFirst & pSecond) / len(vUnion)) if vUnion else 0

    return rSimilarity


def find_similar_offers(pDatabaseFile, pNow, pLimit):
    """Retourne les offres récentes les plus proches d'une offre retenue.

    Chaque offre porte similarity (sur 100) et reference_title, le titre de
    l'offre retenue qui lui ressemble le plus.
    """

    vReferences = [
        (vOffer.get("title") or "", build_signature(vOffer))
        for vStatus in REFERENCE_STATUSES
        for vOffer in get_offers(pDatabaseFile, pStatus=vStatus).to_dict("records")
    ]

    if not vReferences:
        return []

    vCandidates = [
        vOffer
        for vOffer in get_offers(
            pDatabaseFile,
            pSeenSince=pNow - timedelta(days=SIMILAR_OFFER_DAYS),
            pHideIgnored=True,
        ).to_dict("records")
        if not isinstance(vOffer.get("application_status"), str)
    ]

    rOffers = []

    for vOffer in vCandidates:
        vSignature = build_signature(vOffer)
        vSimilarity, vTitle = max(
            (compute_similarity(vSignature, vReference), vReferenceTitle)
            for vReferenceTitle, vReference in vReferences
        )

        if vSimilarity >= MIN_SIMILARITY:
            rOffers.append(
                {**vOffer, "similarity": vSimilarity, "reference_title": vTitle}
            )

    rOffers.sort(key=lambda pOffer: pOffer["similarity"], reverse=True)

    return rOffers[:pLimit]


def mark_like_ignored(pDatabaseFile, pOffers):
    """Signale par like_ignored les offres très proches d'une offre ignorée, avec
    son titre ; une offre déjà suivie n'est jamais signalée.
    """

    vIgnored = [
        (vOffer.get("title") or "", build_signature(vOffer))
        for vOffer in get_offers(pDatabaseFile, pStatus="IGNORED").to_dict("records")
    ]

    for vOffer in pOffers:
        vOffer["like_ignored"] = None

        if not vIgnored or isinstance(vOffer.get("application_status"), str):
            continue

        vSignature = build_signature(vOffer)
        vSimilarity, vTitle = max(
            (compute_similarity(vSignature, vReference), vReferenceTitle)
            for vReferenceTitle, vReference in vIgnored
        )

        if vSimilarity >= LIKE_IGNORED_SIMILARITY:
            vOffer["like_ignored"] = vTitle
