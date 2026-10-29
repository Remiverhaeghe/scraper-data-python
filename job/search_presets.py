"""Recherches prêtes à l'emploi, enregistrées d'un clic"""

import re

from job.geocoding import load_home
from job.sources.configuration import DEFAULT_CRITERIA
from job.sources.registry import SOURCES
from storage.saved_searches import save_search

# Métiers industriels cherchés, un par recherche : les sources qui cherchent
# côté serveur n'acceptent qu'un mot-clé à la fois. Intitulés au singulier, tels
# que les recruteurs les écrivent (SNCF, Keolis, industriels du Nord).
INDUSTRY_KEYWORDS = (
    "Maintenance",
    "Technicien de maintenance",
    "Maintenance ferroviaire",
    "Électrotechnique",
    "Électrotechnicien",
    "Automatisme",
    "GMAO",
    "Planificateur maintenance",
)

# Sources cochées : offres en France et pages carrière des entreprises suivies
INDUSTRY_CATEGORIES = ("france", "company")

INDUSTRY_MAX_ITEMS = 100

# Métiers cherchés autour du domicile : développement et industrie
LOCAL_KEYWORDS = (
    "Java",
    "PHP",
    "Développeur",
    "Maintenance",
    "Technicien de maintenance",
    "Électrotechnicien",
    "Ferroviaire",
    "Automatisme",
)

# Rayon des recherches locales sans rayon d'alerte réglé
DEFAULT_LOCAL_RADIUS_KM = 30

# Ville en fin de libellé du géocodeur : « Rue X 59100 Roubaix »
CITY_PATTERN = re.compile(r"\d{5}\s+(.+)$")


def create_industry_searches(pDatabaseFile, pNow):
    """Enregistre une recherche par métier industriel ; retourne leurs noms.

    Une recherche du même nom, déjà enregistrée, est remplacée.
    """

    vSources = [
        vName
        for vName, vDefinition in SOURCES.items()
        if vDefinition.category in INDUSTRY_CATEGORIES
    ]

    rNames = [
        save_search(
            pDatabaseFile,
            f"Industrie · {vKeyword}",
            vSources,
            {
                **DEFAULT_CRITERIA,
                "keyword": vKeyword.lower(),
                "max_items": INDUSTRY_MAX_ITEMS,
            },
            pNow,
        )
        for vKeyword in INDUSTRY_KEYWORDS
    ]

    return rNames


def read_home_city(pHome):
    """Retourne la ville du domicile, lue après le code postal du libellé."""

    vMatch = CITY_PATTERN.search(pHome["label"])

    rCity = vMatch.group(1) if vMatch else pHome["label"]

    return rCity


def create_local_searches(pDatabaseFile, pNow):
    """Enregistre une recherche par métier autour du domicile ; retourne leurs noms.

    Lève ValueError sans domicile renseigné. Le rayon est celui des alertes,
    ou DEFAULT_LOCAL_RADIUS_KM s'il n'est pas réglé.
    """

    vHome = load_home(pDatabaseFile)

    if vHome is None:
        raise ValueError("Renseignez d'abord votre domicile dans Paramètres.")

    vCity = read_home_city(vHome)
    vRadius = vHome.get("alert_radius_km") or DEFAULT_LOCAL_RADIUS_KM
    vSources = [
        vName
        for vName, vDefinition in SOURCES.items()
        if vDefinition.category in INDUSTRY_CATEGORIES
    ]

    rNames = [
        save_search(
            pDatabaseFile,
            f"Près de chez moi · {vKeyword}",
            vSources,
            {
                **DEFAULT_CRITERIA,
                "keyword": vKeyword.lower(),
                "location": vCity,
                "max_distance_km": vRadius,
                "max_items": INDUSTRY_MAX_ITEMS,
            },
            pNow,
        )
        for vKeyword in LOCAL_KEYWORDS
    ]

    return rNames
