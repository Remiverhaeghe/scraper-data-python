"""Employeurs industriels de la région, tirés de l'annuaire public des entreprises

La liste vient de l'API Recherche d'entreprises de l'État (gratuite, sans clé) :
les entreprises industrielles, d'énergie et de transport d'au moins 250
salariés qui ont un site dans la région, rangées par secteur d'après leur code
d'activité. Suivre un employeur l'ajoute aux entreprises privilégiées : ses
nouvelles offres sont alors signalées par la veille existante.
"""

import time
from datetime import datetime

import requests

from job.company_info import COMPANY_PAGE_URL, COMPANY_SEARCH_URL, find_nearest_site
from job.companies import add_company_rule, get_company_keys, load_company_rules
from job.fingerprint import normalize_company
from job.geocoding import load_home
from storage.job_offers import get_offers
from storage.settings_repository import load_json_setting, save_json_setting
from utils.api_client import request_json
from utils.logger import get_logger

logger = get_logger(__name__)

LOCAL_EMPLOYERS_KEY = "local_employers"
REGION = "Hauts-de-France"
REGION_DEPARTMENTS = ("02", "59", "60", "62", "80")
# Industrie manufacturière, énergie, transports
SECTIONS = ("C", "D", "H")
# Tranches INSEE de 250 salariés et plus : de vrais services de maintenance
EMPLOYEE_RANGES = "32,41,42,51,52,53"
PER_PAGE = 25
MAX_PAGES = 12
# L'API accepte 7 appels par seconde : une pause entre deux pages suffit
PAUSE_SECONDS = 0.2

# Secteur d'après les deux premiers chiffres du code d'activité (NAF)
SECTORS = {
    "Agroalimentaire": ("10", "11"),
    "Chimie, pharmacie, plasturgie": ("20", "21", "22"),
    "Énergie": ("35",),
    "Matériel de transport": ("29", "30"),
    "Transport et logistique": ("49", "50", "51", "52", "53"),
    "Métallurgie et mécanique": ("24", "25", "28", "33"),
}
OTHER_SECTOR = "Autre industrie"


def get_sector(pActivity):
    """Retourne le secteur d'un code d'activité NAF, « Autre industrie » à défaut."""

    vDivision = str(pActivity or "")[:2]

    rSector = next(
        (vSector for vSector, vDivisions in SECTORS.items() if vDivision in vDivisions),
        OTHER_SECTOR,
    )

    return rSector


def describe_employer(pResult, pHome):
    """Traduit un résultat de l'API en employeur : nom, secteur, sites, distance."""

    vNearest = find_nearest_site(pResult, pHome)

    rEmployer = {
        "siren": pResult.get("siren"),
        "name": pResult.get("nom_complet") or pResult.get("nom_raison_sociale") or "",
        "names": [
            vName
            for vName in (
                pResult.get("nom_complet"),
                pResult.get("nom_raison_sociale"),
                pResult.get("sigle"),
            )
            if vName
        ],
        "sector": get_sector(pResult.get("activite_principale")),
        "activity": pResult.get("activite_principale"),
        "category": pResult.get("categorie_entreprise"),
        "sites": len(pResult.get("matching_etablissements") or []),
        "city": vNearest["city"] if vNearest else "",
        "distance_km": vNearest["distance_km"] if vNearest else None,
        "page": COMPANY_PAGE_URL.format(siren=pResult.get("siren")),
    }

    return rEmployer


def fetch_local_employers(
    pDatabaseFile, pNow=None, pRequest=request_json, pPause=PAUSE_SECONDS
):
    """Interroge l'annuaire public et enregistre la liste ; retourne le nombre d'employeurs.

    Lève ValueError si le service ne répond pas : la liste précédente est gardée.
    """

    vHome = load_home(pDatabaseFile)
    vEmployers = {}

    try:
        for vDepartment in REGION_DEPARTMENTS:
            for vSection in SECTIONS:
                vPage = 1
                vPages = 1

                while vPage <= min(vPages, MAX_PAGES):
                    vData = pRequest(
                        "GET",
                        COMPANY_SEARCH_URL,
                        pParams={
                            "section_activite_principale": vSection,
                            "departement": vDepartment,
                            "tranche_effectif_salarie": EMPLOYEE_RANGES,
                            "etat_administratif": "A",
                            "per_page": PER_PAGE,
                            "page": vPage,
                        },
                    )
                    vPages = int(vData.get("total_pages") or 1)

                    for vResult in vData.get("results") or []:
                        vEmployer = describe_employer(vResult, vHome)
                        vKnown = vEmployers.get(vEmployer["siren"])

                        # Une entreprise présente dans plusieurs départements garde son site le plus proche
                        if vKnown is None or (
                            vEmployer["distance_km"] is not None
                            and (
                                vKnown["distance_km"] is None
                                or vEmployer["distance_km"] < vKnown["distance_km"]
                            )
                        ):
                            vEmployers[vEmployer["siren"]] = vEmployer

                    vPage += 1
                    time.sleep(pPause)

    except (requests.RequestException, ValueError) as vError:
        logger.warning("Annuaire des entreprises injoignable : %s", vError)
        raise ValueError(
            "Le service public de recherche d'entreprises ne répond pas, réessayez plus tard."
        ) from vError

    save_json_setting(
        pDatabaseFile,
        LOCAL_EMPLOYERS_KEY,
        {
            "updated_at": (pNow or datetime.now()).isoformat(timespec="seconds"),
            "employers": list(vEmployers.values()),
        },
    )
    logger.info("Employeurs de la région mis à jour : %d", len(vEmployers))

    rCount = len(vEmployers)

    return rCount


def build_employers_view(pDatabaseFile, pSector="", pMaxDistance=None):
    """Retourne les employeurs à afficher : filtrés, du plus proche au plus loin.

    Chacun indique ses offres en base et s'il est suivi (entreprise privilégiée).
    """

    vData = load_json_setting(pDatabaseFile, LOCAL_EMPLOYERS_KEY, {}, dict)
    vPreferred = set(get_company_keys(load_company_rules(pDatabaseFile), "preferred"))
    vOfferCounts = {}

    for vCompany in get_offers(pDatabaseFile, pHideIgnored=True)["company"].dropna():
        vKey = normalize_company(vCompany)
        vOfferCounts[vKey] = vOfferCounts.get(vKey, 0) + 1

    vEmployers = []

    for vEmployer in vData.get("employers") or []:
        if pSector and vEmployer.get("sector") != pSector:
            continue

        if pMaxDistance and (vEmployer.get("distance_km") or 0) > pMaxDistance:
            continue

        vKeys = {normalize_company(vName) for vName in vEmployer.get("names", [])} - {
            ""
        }
        vEmployers.append(
            {
                **vEmployer,
                "offers": sum(vOfferCounts.get(vKey, 0) for vKey in vKeys),
                "followed": bool(vKeys & vPreferred),
            }
        )

    vEmployers.sort(
        key=lambda pEmployer: (
            pEmployer["distance_km"] is None,
            pEmployer["distance_km"] or 0,
            pEmployer["name"],
        )
    )

    rView = {
        "region": REGION,
        "updated_at": vData.get("updated_at"),
        "sectors": [*SECTORS, OTHER_SECTOR],
        "employers": vEmployers,
        "count": len(vData.get("employers") or []),
    }

    return rView


def follow_employer(pDatabaseFile, pSiren):
    """Suit un employeur : chacun de ses noms rejoint les entreprises privilégiées.

    Lève ValueError pour un employeur absent de la liste.
    """

    vEmployer = next(
        (
            vItem
            for vItem in load_json_setting(
                pDatabaseFile, LOCAL_EMPLOYERS_KEY, {}, dict
            ).get("employers")
            or []
            if vItem.get("siren") == pSiren
        ),
        None,
    )

    if vEmployer is None:
        raise ValueError("Employeur absent de la liste : mettez-la à jour.")

    # Les offres reprennent le nom complet, la raison sociale ou le sigle
    for vName in dict.fromkeys(vEmployer.get("names") or [vEmployer["name"]]):
        add_company_rule(pDatabaseFile, vName, "preferred")

    logger.info("Employeur suivi : %s", vEmployer["name"])
