"""Score de fraîcheur d'une offre et annonces en ligne depuis longtemps"""

from datetime import datetime

# Au-delà, une offre a perdu tout son intérêt de fraîcheur
FRESHNESS_DAYS = 30

# Une même offre publiée par une source de plus est plus visible, donc plus disputée
EXTRA_SOURCE_POINTS = 10

# Au-delà, une annonce encore en ligne est signalée : poste difficile à pourvoir,
# ou annonce republiée pour constituer un vivier de candidats.
RECURRING_DAYS = 45

# Écart entre la publication annoncée et la première vue au-delà duquel l'offre
# est dite republiée (vue bien avant sa « publication ») ou ancienne chez la
# source (publiée bien avant d'être trouvée).
SOURCE_GAP_DAYS = 30


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


def read_date(pValue):
    """Retourne une date ISO en datetime, ou None si elle est absente ou illisible."""

    try:
        rDate = datetime.fromisoformat(str(pValue)[:19]) if pValue else None

    except ValueError:
        rDate = None

    return rDate


def describe_source_age(pOffer):
    """Retourne (republiée, ancienneté chez la source en jours ou None).

    La publication annoncée par la source est comparée à la première vue.
    """

    vPublished = read_date(pOffer.get("published_at"))
    vFirstSeen = read_date(pOffer.get("first_seen_at"))

    if vPublished is None or vFirstSeen is None:
        return (False, None)

    vGap = (vPublished - vFirstSeen).days

    rAge = (
        vGap > SOURCE_GAP_DAYS,
        -vGap if -vGap > SOURCE_GAP_DAYS else None,
    )

    return rAge


def add_freshness(pOffers, pNow):
    """Ajoute à chaque offre regroupée son score de fraîcheur et son ancienneté.

    recurring_days n'est donné qu'au-delà de RECURRING_DAYS, sinon None.
    """

    for vOffer in pOffers:
        vOffer["freshness"] = compute_freshness(vOffer, pNow)

        vDays = count_online_days(vOffer, pNow)
        vOffer["recurring_days"] = vDays if vDays >= RECURRING_DAYS else None
        vOffer["republished"], vOffer["old_at_source_days"] = describe_source_age(
            vOffer
        )
