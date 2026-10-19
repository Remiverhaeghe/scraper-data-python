"""Score de fraîcheur d'une offre : récente et publiée par plusieurs sources"""

from datetime import datetime

# Au-delà, une offre a perdu tout son intérêt de fraîcheur
FRESHNESS_DAYS = 30

# Une même offre publiée par une source de plus est plus visible, donc plus disputée
EXTRA_SOURCE_POINTS = 10


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


def get_freshness_tone(pScore):
    """Retourne la couleur d'un score : vert, orange ou gris."""

    rTone = "success" if pScore >= 70 else ("warning" if pScore >= 40 else "muted")

    return rTone


def add_freshness(pOffers, pNow):
    """Ajoute le score de fraîcheur à chaque offre, après leur regroupement."""

    for vOffer in pOffers:
        vOffer["freshness"] = compute_freshness(vOffer, pNow)
