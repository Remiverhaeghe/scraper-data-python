"""Agences d'intérim et de placement, reconnues pour masquer leurs annonces"""

import re

from job.fingerprint import normalize, normalize_company
from storage.settings_repository import load_json_setting, save_json_setting
from utils.logger import get_logger

logger = get_logger(__name__)

AGENCIES_KEY = "interim_agencies"

AGENCY_SEPARATORS = re.compile(r"[,;\n]")

# Noms normalisés (job.fingerprint.normalize_company) : cherchés comme mot dans
# le nom de l'entreprise, « adecco medical » ou « proman 123 » compris.
INTERIM_AGENCIES = (
    "abalone",
    "actual",
    "adecco",
    "aston interim",
    "atoll interim",
    "camo emploi",
    "crit",
    "domino rh",
    "ergalis",
    "expectra",
    "gojob",
    "groupe fed",
    "id interim",
    "interim nation",
    "kelly services",
    "leader interim",
    "lynx rh",
    "manpower",
    "partnaire",
    "proman",
    "randstad",
    "ressources interim",
    "samsic emploi",
    "staffmatch",
    "start people",
    "supplay",
    "synergie",
    "temporis",
    "triangle interim",
)

# Mentions d'une annonce publiée par une agence pour le compte d'un client
AGENCY_MENTIONS = ("agence d'intérim", "agence d’intérim", "agence d'interim")


def load_interim_agencies(pDatabaseFile):
    """Retourne les agences reconnues : la liste enregistrée, sinon celle par défaut."""

    rAgencies = load_json_setting(pDatabaseFile, AGENCIES_KEY, None, list) or list(
        INTERIM_AGENCIES
    )

    return rAgencies


def save_interim_agencies(pDatabaseFile, pText):
    """Enregistre les agences saisies, séparées par des virgules ; vide, rétablit
    la liste par défaut. Retourne la liste en vigueur.
    """

    vAgencies = sorted(
        {
            vAgency
            for vAgency in map(normalize_company, AGENCY_SEPARATORS.split(pText or ""))
            if vAgency
        }
    )

    save_json_setting(pDatabaseFile, AGENCIES_KEY, vAgencies or None)

    logger.info(
        "Agences d'intérim : %s",
        f"{len(vAgencies)} enregistrée(s)" if vAgencies else "liste par défaut",
    )

    rAgencies = vAgencies or list(INTERIM_AGENCIES)

    return rAgencies


def is_agency_offer(pOffer, pAgencies):
    """Indique si une offre est publiée par une agence de la liste, ou se présente
    comme telle dans sa description.
    """

    vCompany = f" {normalize_company(pOffer.get('company'))} "
    vDescription = normalize(pOffer.get("description"))

    rAgency = any(f" {vAgency} " in vCompany for vAgency in pAgencies) or any(
        normalize(vMention) in vDescription for vMention in AGENCY_MENTIONS
    )

    return rAgency


def mark_agency_offers(pOffers, pAgencies):
    """Signale par is_agency les offres des agences d'intérim."""

    for vOffer in pOffers:
        vOffer["is_agency"] = is_agency_offer(vOffer, pAgencies)
