"""Position du domicile et des offres en France, pour filtrer par distance"""

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

# Rayons proposés dans les filtres, en kilomètres ; 0 désactive le filtre.
DISTANCE_FILTERS = {
    0: "Toute distance",
    10: "À 10 km",
    25: "À 25 km",
    50: "À 50 km",
    100: "À 100 km",
}


def geocode(pQuery, pType=None, pNear=None):
    """Retourne ((latitude, longitude), libellé) du lieu cherché, ou None.

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
        rPlace = ((vLatitude, vLongitude), vFeature["properties"].get("label", ""))

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

        (vLatitude, vLongitude), vLabel = vPlace
        rHome = {
            "address": vAddress,
            "label": vLabel,
            "latitude": vLatitude,
            "longitude": vLongitude,
        }

    save_json_setting(pDatabaseFile, HOME_KEY, rHome)

    # Le libellé suffit au diagnostic : l'adresse exacte n'a rien à faire au journal.
    logger.info("Domicile %s", f"enregistré : {rHome['label']}" if rHome else "effacé")

    return rHome


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
    vPositions = []
    rReport = {"located": 0, "lookups": 0, "unknown": 0}

    for vSource, vSourceId, vLocation in get_offers_to_locate(pDatabaseFile, FRANCE):
        vKey = normalize(vLocation)

        if not is_locatable(vKey):
            continue

        if vKey not in vCache:
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
            rReport["unknown"] += vPlace is None
            save_location(pDatabaseFile, vKey, vCache[vKey], vPlace and vPlace[1], vNow)

        if vCache[vKey]:
            vPositions.append((*vCache[vKey], vSource, vSourceId))

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
