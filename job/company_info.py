"""Informations publiques sur une entreprise française, sans clé ni service payant"""

import requests

from job.geocoding import compute_distance_km
from utils.api_client import request_json
from utils.logger import get_logger

logger = get_logger(__name__)

# API Recherche d'entreprises de l'État : gratuite, sans compte, données INSEE et RNE
COMPANY_SEARCH_URL = "https://recherche-entreprises.api.gouv.fr/search"
COMPANY_PAGE_URL = "https://annuaire-entreprises.data.gouv.fr/entreprise/{siren}"

# Plusieurs sociétés portent souvent le même nom (holding, filiales) : les
# premières sont proposées, l'utilisateur reconnaît la bonne.
MAX_COMPANY_RESULTS = 3

# Sections de la nomenclature d'activités française (NAF)
ACTIVITY_SECTIONS = {
    "A": "Agriculture, sylviculture et pêche",
    "B": "Industries extractives",
    "C": "Industrie manufacturière",
    "D": "Production et distribution d'énergie",
    "E": "Eau, assainissement, gestion des déchets",
    "F": "Construction",
    "G": "Commerce, réparation automobile",
    "H": "Transports et entreposage",
    "I": "Hébergement et restauration",
    "J": "Information et communication",
    "K": "Activités financières et d'assurance",
    "L": "Activités immobilières",
    "M": "Activités spécialisées, scientifiques et techniques",
    "N": "Services administratifs et de soutien",
    "O": "Administration publique",
    "P": "Enseignement",
    "Q": "Santé humaine et action sociale",
    "R": "Arts, spectacles et activités récréatives",
    "S": "Autres activités de services",
    "T": "Activités des ménages en tant qu'employeurs",
    "U": "Activités extra-territoriales",
}

# Tranches d'effectif salarié de l'INSEE
EMPLOYEE_RANGES = {
    "00": "aucun salarié",
    "01": "1 ou 2 salariés",
    "02": "3 à 5 salariés",
    "03": "6 à 9 salariés",
    "11": "10 à 19 salariés",
    "12": "20 à 49 salariés",
    "21": "50 à 99 salariés",
    "22": "100 à 199 salariés",
    "31": "200 à 249 salariés",
    "32": "250 à 499 salariés",
    "41": "500 à 999 salariés",
    "42": "1 000 à 1 999 salariés",
    "51": "2 000 à 4 999 salariés",
    "52": "5 000 à 9 999 salariés",
    "53": "10 000 salariés et plus",
}

CATEGORIES = {
    "PME": "Petite ou moyenne entreprise",
    "ETI": "Entreprise de taille intermédiaire",
    "GE": "Grande entreprise",
}


def format_revenue(pFinances):
    """Retourne le dernier chiffre d'affaires publié, ou None."""

    rRevenue = None

    vYears = sorted(
        (vYear for vYear, vValues in (pFinances or {}).items() if vValues.get("ca")),
        reverse=True,
    )

    if vYears:
        vAmount = pFinances[vYears[0]]["ca"]

        if vAmount >= 1_000_000_000:
            vText = f"{vAmount / 1_000_000_000:.1f} Md€".replace(".", ",")
        else:
            vText = f"{vAmount / 1_000_000:.1f} M€".replace(".", ",")

        rRevenue = f"{vText} en {vYears[0]}"

    return rRevenue


def find_nearest_site(pResult, pHome):
    """Retourne la commune et la distance de l'établissement ouvert le plus proche.

    Retourne None sans domicile ou sans établissement placé.
    """

    if not pHome:
        return None

    vSites = []

    for vSite in pResult.get("matching_etablissements") or []:
        try:
            vPosition = (float(vSite["latitude"]), float(vSite["longitude"]))

        except (KeyError, TypeError, ValueError):
            continue

        if vSite.get("etat_administratif") != "F":
            vSites.append(
                (
                    compute_distance_km(
                        (pHome["latitude"], pHome["longitude"]), vPosition
                    ),
                    vSite.get("libelle_commune") or "",
                )
            )

    rNearest = None

    if vSites:
        vDistance, vCity = min(vSites)
        rNearest = {"city": vCity.title(), "distance_km": round(vDistance)}

    return rNearest


def describe_company(pResult, pHome=None):
    """Traduit un résultat de l'API en informations lisibles."""

    vSiege = pResult.get("siege") or {}

    rCompany = {
        "name": pResult.get("nom_complet") or "Nom non diffusé",
        "siren": pResult.get("siren"),
        "activity": ACTIVITY_SECTIONS.get(pResult.get("section_activite_principale")),
        "activity_code": pResult.get("activite_principale"),
        "employees": EMPLOYEE_RANGES.get(pResult.get("tranche_effectif_salarie")),
        "category": CATEGORIES.get(pResult.get("categorie_entreprise")),
        "created": (pResult.get("date_creation") or "")[:4] or None,
        "city": vSiege.get("libelle_commune"),
        "revenue": format_revenue(pResult.get("finances")),
        "active": pResult.get("etat_administratif") != "C",
        "sites": pResult.get("nombre_etablissements_ouverts"),
        "nearest": find_nearest_site(pResult, pHome),
        "url": (
            COMPANY_PAGE_URL.format(siren=pResult["siren"])
            if pResult.get("siren")
            else None
        ),
    }

    return rCompany


def lookup_company(pName, pHome=None):
    """Cherche une entreprise française par son nom ; retourne les meilleurs résultats.

    Avec pHome, chaque entreprise indique son établissement le plus proche.

    Lève ValueError avec un message lisible si le service ne répond pas.
    """

    vName = " ".join(str(pName or "").split())

    if len(vName) < 3:
        raise ValueError("Nom d'entreprise trop court pour une recherche.")

    try:
        vData = request_json(
            "GET",
            COMPANY_SEARCH_URL,
            pParams={"q": vName, "per_page": MAX_COMPANY_RESULTS, "page": 1},
        )

    except (requests.RequestException, ValueError) as vError:
        # Le nom cherché n'est pas sensible ; le détail aide à diagnostiquer.
        logger.warning(
            "Recherche d'entreprise impossible pour « %s » : %s", vName, vError
        )
        raise ValueError(
            "Le service public de recherche d'entreprises ne répond pas, "
            "réessayez plus tard."
        ) from vError

    rCompanies = [
        describe_company(vResult, pHome)
        for vResult in (vData.get("results") or [])[:MAX_COMPANY_RESULTS]
    ]

    logger.info(
        "Recherche d'entreprise « %s » : %s résultat(s)", vName, len(rCompanies)
    )

    return rCompanies


def summarize_company(pCompany):
    """Résume une entreprise en une ligne, pour l'affichage et les demandes à ChatGPT."""

    vParts = [
        pCompany["activity"],
        pCompany["category"],
        pCompany["employees"],
        f"créée en {pCompany['created']}" if pCompany["created"] else None,
        f"siège à {pCompany['city'].title()}" if pCompany["city"] else None,
        f"chiffre d'affaires {pCompany['revenue']}" if pCompany["revenue"] else None,
        (
            f"{pCompany['sites']} établissement(s) ouvert(s)"
            if pCompany.get("sites")
            else None
        ),
        (
            f"le plus proche à {pCompany['nearest']['city']} "
            f"({pCompany['nearest']['distance_km']} km de chez vous)"
            if pCompany.get("nearest")
            else None
        ),
        None if pCompany["active"] else "fermée",
    ]

    rSummary = f"{pCompany['name']} : " + ", ".join(vPart for vPart in vParts if vPart)

    return rSummary
