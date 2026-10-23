"""Archivage des offres expirées : supprimées après une sauvegarde, une fois par jour

Seules les offres sans candidature, relance, pièce jointe ni note d'entretien
sont concernées (storage/maintenance.get_purgeable_offers). Le délai ne descend
jamais sous celui d'une offre expirée.
"""

from datetime import timedelta

from job.settings import load_settings
from storage.maintenance import delete_offers, get_purgeable_offers
from storage.settings_repository import get_setting_values, save_setting_values
from utils.logger import get_logger

logger = get_logger(__name__)

# Date du dernier archivage, pour n'en faire qu'un par jour
LAST_ARCHIVE_KEY = "offer_archive_day"


def find_offers_to_archive(pDatabaseFile, pNow):
    """Retourne les offres non suivies absentes des recherches depuis le délai réglé."""

    vSettings = load_settings(pDatabaseFile)
    vDays = vSettings["archive_after_days"]

    if not vDays:
        return []

    vLimit = (pNow - timedelta(days=max(vDays, vSettings["expiry_days"]))).isoformat()

    rOffers = [
        vOffer
        for vOffer in get_purgeable_offers(pDatabaseFile)
        if (vOffer["last_seen_at"] or vOffer["first_seen_at"] or "") < vLimit
    ]

    return rOffers


def archive_expired_offers(pDatabaseFile, pNow):
    """Archive les offres expirées, au plus une fois par jour ; retourne leur nombre."""

    vToday = pNow.date().isoformat()

    if get_setting_values(pDatabaseFile).get(LAST_ARCHIVE_KEY) == vToday:
        return 0

    vOffers = find_offers_to_archive(pDatabaseFile, pNow)

    if vOffers:
        delete_offers(
            pDatabaseFile,
            [(vOffer["source"], vOffer["source_id"]) for vOffer in vOffers],
            pNow,
        )
        logger.info("Archivage : %s offre(s) expirée(s) supprimée(s)", len(vOffers))

    save_setting_values(pDatabaseFile, {LAST_ARCHIVE_KEY: vToday})

    rCount = len(vOffers)

    return rCount
