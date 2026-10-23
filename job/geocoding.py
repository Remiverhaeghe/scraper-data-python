"""Position du domicile et des offres en France, pour filtrer par distance"""

import math
from datetime import datetime

import requests

from job.fingerprint import normalize
from job.location import (
    COUNTRY_ALIASES,
    FRANCE,
    FRENCH_REGION_PATTERN,
    WORLD_REGIONS,
    find_department,
)
from storage.geo_cache import (
    get_cached_departments,
    get_cached_locations,
    get_offers_to_locate,
    save_location,
    save_offer_positions,
)
from storage.settings_repository import load_json_setting, save_json_setting
from utils.api_client import request_json
from utils.logger import get_logger

logger = get_logger(__name__)

# Géocodeur de l'IGN (Base Adresse Nationale), gratuit et sans clé
GEOCODING_URL = "https://data.geopf.fr/geocodage/search"

# En dessous, le lieu trouvé ressemble trop peu au lieu cherché.
MIN_SCORE = 0.4

# Recherches réseau par passage : les suivantes attendent le passage suivant.
MAX_LOOKUPS = 300

HOME_KEY = "home_location"
EARTH_RADIUS_KM = 6371

# Rayons proposés dans les filtres, en kilomètres ; 0 désactive le filtre.
DISTANCE_FILTERS = {
    0: "Toute distance",
    10: "À 10 km",
    25: "À 25 km",
    50: "À 50 km",
    100: "À 100 km",
}


def geocode(pQuery, pType=None, pNear=None):
    """Retourne ((latitude, longitude), libellé, département) du lieu, ou None.

    pNear, la position du domicile, départage les homonymes (Saint-Denis).
    """

    vParams = {"q": pQuery[:200], "limit": 1}

    if pType:
        vParams["type"] = pType

    if pNear:
        vParams["lat"], vParams["lon"] = pNear

    vData = request_json(
        "GET",
        GEOCODING_URL,
        pParams=vParams,
        pHeaders={"Accept": "application/json"},
        pTimeout=10,
    )
    vFeature = next(iter(vData.get("features") or []), None)
    rPlace = None

    if vFeature and vFeature["properties"].get("score", 0) >= MIN_SCORE:
        vLongitude, vLatitude = vFeature["geometry"]["coordinates"]
        vProperties = vFeature["properties"]
        # Contexte de la base d'adresses : « 59, Nord, Hauts-de-France »
        vDepartment = str(vProperties.get("context") or "").split(",", 1)[0].strip()
        rPlace = ((vLatitude, vLongitude), vProperties.get("label", ""), vDepartment)

    return rPlace


def load_home(pDatabaseFile):
    """Retourne le domicile enregistré : adresse, libellé et position, ou None."""

    rHome = load_json_setting(pDatabaseFile, HOME_KEY, None, dict)

    return rHome


def save_home(pDatabaseFile, pAddress):
    """Cherche l'adresse du domicile et l'enregistre ; vide, l'efface.

    Retourne le domicile, ou None une fois effacé ; lève ValueError si
    l'adresse est introuvable et requests.RequestException sans réseau.
    """

    vAddress = " ".join(str(pAddress or "").split())
    rHome = None

    if vAddress:
        vPlace = geocode(vAddress)

        if vPlace is None:
            raise ValueError(
                "Adresse introuvable : précisez la ville ou le code postal."
            )

        (vLatitude, vLongitude), vLabel, _ = vPlace
        rHome = {
            "address": vAddress,
            "label": vLabel,
            "latitude": vLatitude,
            "longitude": vLongitude,
            "alert_radius_km": (load_home(pDatabaseFile) or {}).get(
                "alert_radius_km", 0
            ),
        }

    save_json_setting(pDatabaseFile, HOME_KEY, rHome)

    # Le libellé suffit au diagnostic : l'adresse exacte n'a rien à faire au journal.
    logger.info("Domicile %s", f"enregistré : {rHome['label']}" if rHome else "effacé")

    return rHome


def save_alert_radius(pDatabaseFile, pRadiusKm):
    """Enregistre le rayon des alertes autour du domicile ; 0 garde toutes les offres."""

    vHome = load_home(pDatabaseFile)

    if vHome is None:
        raise ValueError("Enregistrez d'abord le domicile.")

    vHome["alert_radius_km"] = pRadiusKm if pRadiusKm in DISTANCE_FILTERS else 0
    save_json_setting(pDatabaseFile, HOME_KEY, vHome)

    logger.info("Rayon des alertes : %s km", vHome["alert_radius_km"] or "aucun")


def keep_within_alert_radius(pOffers, pHome):
    """Garde les offres dans le rayon des alertes, et celles en télétravail.

    Sans domicile ni rayon, toutes les offres sont gardées ; une offre sans
    position connue est écartée dès qu'un rayon est choisi.
    """

    vRadius = (pHome or {}).get("alert_radius_km") or 0

    rOffers = [
        vOffer
        for vOffer in pOffers
        if not vRadius
        or vOffer.get("remote") is True
        or (vOffer.get("distance_km") is not None and vOffer["distance_km"] <= vRadius)
    ]

    return rOffers


def is_locatable(pKey):
    """Indique si un lieu normalisé désigne une ville, et non un pays ou une zone."""

    rLocatable = bool(pKey) and not (
        pKey in COUNTRY_ALIASES
        or pKey in WORLD_REGIONS
        or FRENCH_REGION_PATTERN.fullmatch(pKey)
        or find_department(pKey)
    )

    return rLocatable


def locate_offers(pDatabaseFile, pNow=None, pMaxLookups=MAX_LOOKUPS):
    """Donne une position aux offres françaises qui n'en ont pas encore.

    Chaque lieu n'est cherché qu'une fois, puis lu dans le cache. Retourne le
    bilan : offres placées, lieux cherchés et lieux restés inconnus.
    """

    vNow = pNow or datetime.now()
    vHome = load_home(pDatabaseFile)
    vNear = (vHome["latitude"], vHome["longitude"]) if vHome else None
    vCache = get_cached_locations(pDatabaseFile)
    vDepartments = get_cached_departments(pDatabaseFile)
    vPositions = []
    rReport = {"located": 0, "lookups": 0, "unknown": 0}

    for vSource, vSourceId, vLocation in get_offers_to_locate(pDatabaseFile, FRANCE):
        vKey = normalize(vLocation)

        if not is_locatable(vKey):
            continue

        # Lieu jamais cherché, ou placé avant que le département soit gardé
        if vKey not in vCache or (vCache[vKey] and vDepartments.get(vKey) is None):
            if rReport["lookups"] >= pMaxLookups:
                continue

            try:
                vPlace = geocode(vLocation, "municipality", vNear)

            except (requests.RequestException, ValueError) as vException:
                logger.warning(
                    "Géocodage interrompu (%s) : reprise au prochain passage",
                    vException,
                )
                break

            rReport["lookups"] += 1
            vCache[vKey] = vPlace[0] if vPlace else None
            # Chaîne vide : cherché sans département connu, à ne pas chercher de nouveau.
            vDepartments[vKey] = (vPlace[2] or "") if vPlace else None
            rReport["unknown"] += vPlace is None
            save_location(
                pDatabaseFile,
                vKey,
                vCache[vKey],
                vPlace and vPlace[1],
                vNow,
                vDepartments[vKey],
            )

        if vCache[vKey]:
            vPositions.append(
                (*vCache[vKey], vDepartments.get(vKey) or "", vSource, vSourceId)
            )

    save_offer_positions(pDatabaseFile, vPositions)
    rReport["located"] = len(vPositions)

    if vPositions or rReport["lookups"]:
        logger.info(
            "Offres placées : %s ; lieux cherchés : %s, dont %s inconnu(s)",
            rReport["located"],
            rReport["lookups"],
            rReport["unknown"],
        )

    return rReport


def locate_all_offers(pDatabaseFile, pNow=None):
    """Place toutes les offres en une fois, passage après passage ; retourne le bilan.

    S'arrête quand un passage n'atteint plus la limite de recherches : tout est
    placé, ou le géocodeur ne répond plus.
    """

    rReport = {"located": 0, "lookups": 0, "unknown": 0}

    while True:
        vReport = locate_offers(pDatabaseFile, pNow, MAX_LOOKUPS)
        rReport = {
            "located": rReport["located"] + vReport["located"],
            "lookups": rReport["lookups"] + vReport["lookups"],
            "unknown": rReport["unknown"] + vReport["unknown"],
        }

        if vReport["lookups"] < MAX_LOOKUPS:
            break

    return rReport


def compute_distance_km(pFrom, pTo):
    """Retourne la distance à vol d'oiseau entre deux positions, en kilomètres."""

    vLatitude1, vLongitude1 = map(math.radians, pFrom)
    vLatitude2, vLongitude2 = map(math.radians, pTo)

    vHalfChord = (
        math.sin((vLatitude2 - vLatitude1) / 2) ** 2
        + math.cos(vLatitude1)
        * math.cos(vLatitude2)
        * math.sin((vLongitude2 - vLongitude1) / 2) ** 2
    )

    rDistance = 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(vHalfChord))

    return rDistance


def read_position(pOffer):
    """Retourne la position enregistrée d'une offre, ou None (NaN des DataFrame compris)."""

    try:
        vPosition = (float(pOffer.get("latitude")), float(pOffer.get("longitude")))

    except (TypeError, ValueError):
        return None

    rPosition = None if any(map(math.isnan, vPosition)) else vPosition

    return rPosition


def add_distances(pOffers, pHome):
    """Ajoute à chaque offre sa distance au domicile en km, ou None si inconnue."""

    vHome = (pHome["latitude"], pHome["longitude"]) if pHome else None

    for vOffer in pOffers:
        vPosition = read_position(vOffer)
        vOffer["distance_km"] = (
            round(compute_distance_km(vHome, vPosition))
            if vHome and vPosition
            else None
        )


def describe_location(pOffer):
    """Retourne le lieu suivi de la distance au domicile quand elle est connue."""

    vLocation = pOffer.get("location") or ""
    vDistance = pOffer.get("distance_km")

    rText = (
        f"{vLocation} · {vDistance} km"
        if vLocation and vDistance is not None
        else vLocation
    )

    return rText
