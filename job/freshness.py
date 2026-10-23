"""Score de fraîcheur d'une offre et annonces en ligne depuis longtemps"""

from datetime import datetime

# Au-delà, une offre a perdu tout son intérêt de fraîcheur
FRESHNESS_DAYS = 30

# Une même offre publiée par une source de plus est plus visible, donc plus disputée
EXTRA_SOURCE_POINTS = 10

# Au-delà, une annonce encore en ligne est signalée : poste difficile à pourvoir,
# ou annonce republiée pour constituer un vivier de candidats.
RECURRING_DAYS = 45


def get_offer_date(pOffer):
    """Retourne la date de publication, ou à défaut de première récupération."""

    rDate = None

    for vKey in ("published_at", "date", "first_seen_at"):
        try:
            rDate = datetime.fromisoformat(str(pOffer.get(vKey))[:19])

        except ValueError:
            continue

        break

    return rDate


def compute_freshness(pOffer, pNow):
    """Retourne un score de 0 à 100 : l'âge de l'offre, majoré par ses sources."""

    vDate = get_offer_date(pOffer)

    rScore = 0

    if vDate is not None:
        vDays = max((pNow - vDate).days, 0)
        vSources = len(pOffer.get("source_labels") or [None])

        rScore = min(
            max(round(100 * (1 - vDays / FRESHNESS_DAYS)), 0)
            + EXTRA_SOURCE_POINTS * (vSources - 1),
            100,
        )

    return rScore


def count_online_days(pOffer, pNow):
    """Retourne le nombre de jours depuis la première annonce vue, doublons compris."""

    vDates = [
        datetime.fromisoformat(str(vAd["first_seen_at"])[:19])
        for vAd in [pOffer, *(pOffer.get("duplicates") or [])]
        if vAd.get("first_seen_at")
    ]

    rDays = (pNow - min(vDates)).days if vDates else 0

    return rDays


def add_freshness(pOffers, pNow):
    """Ajoute à chaque offre regroupée son score de fraîcheur et son ancienneté.

    recurring_days n'est donné qu'au-delà de RECURRING_DAYS, sinon None.
    """

    for vOffer in pOffers:
        vOffer["freshness"] = compute_freshness(vOffer, pNow)

        vDays = count_online_days(vOffer, pNow)
        vOffer["recurring_days"] = vDays if vDays >= RECURRING_DAYS else None
