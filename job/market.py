"""Mon marché : demande et salaires par compétence, région et ville, et leur évolution"""

from datetime import timedelta
from statistics import median

from job.location import FRANCE, find_region, find_region_in_text
from job.preparation import get_offer_skills
from job.presentation import clean_missing_values, format_euros
from job.profile import load_profile
from job.self_assessment import KNOWN_LEVEL, MAX_LEVEL
from job.salary_market import (
    EXCLUDED_CONTRACTS,
    MIN_COMPARABLES,
    get_net_salary,
    is_training,
)
from job.settings import load_settings
from storage.job_offers import get_offers
from utils.logger import get_logger

logger = get_logger(__name__)

# Offres vues sur cette période : le marché d'aujourd'hui, pas celui d'il y a un an
MARKET_DAYS = 90

MAX_SKILL_ROWS = 20
MAX_CITY_ROWS = 10
MAX_REGION_ROWS = 18

# Compétences demandées et peu maîtrisées proposées en priorité
MAX_PRIORITY_SKILLS = 5

# Mois repris dans l'évolution du marché
HISTORY_MONTHS = 6

MONTH_NAMES = (
    "janv.",
    "févr.",
    "mars",
    "avr.",
    "mai",
    "juin",
    "juil.",
    "août",
    "sept.",
    "oct.",
    "nov.",
    "déc.",
)

# Colonnes des tableaux, communes au bureau et au web
MARKET_COLUMNS = ["Offres", "Part", "Avec salaire", "Net mensuel médian"]
SKILL_COLUMNS = ["Compétence", *MARKET_COLUMNS, "Dans mon profil"]
CITY_COLUMNS = ["Ville", *MARKET_COLUMNS]
REGION_COLUMNS = ["Région", *MARKET_COLUMNS]
HISTORY_COLUMNS = ["Mois", "Offres", "Avec vos compétences", "Net mensuel médian"]


def summarize_salaries(pSalaries):
    """Retourne la médiane mise en forme, ou un tiret avec trop peu de salaires."""

    rText = (
        format_euros(median(pSalaries)) if len(pSalaries) >= MIN_COMPARABLES else "—"
    )

    return rText


def build_rows(pGroups, pTotal, pMaxRows, pMine=frozenset()):
    """Retourne les lignes d'un tableau, les plus demandées d'abord."""

    rRows = [
        {
            "name": vName,
            "count": len(vSalaries),
            "share": round(100 * len(vSalaries) / pTotal) if pTotal else 0,
            "salaried": sum(1 for vSalary in vSalaries if vSalary is not None),
            "median": summarize_salaries(
                [vSalary for vSalary in vSalaries if vSalary is not None]
            ),
            "mine": vName in pMine,
        }
        for vName, vSalaries in sorted(
            pGroups.items(), key=lambda pItem: (-len(pItem[1]), pItem[0])
        )[:pMaxRows]
    ]

    return rRows


def build_market_cells(pRow, pWithMine=False):
    """Retourne les textes d'une ligne de tableau, dans l'ordre des colonnes."""

    rCells = [
        pRow["name"],
        str(pRow["count"]),
        f"{pRow['share']} %",
        str(pRow["salaried"]),
        pRow["median"],
    ]

    if pWithMine:
        rCells.append("oui" if pRow["mine"] else "")

    return rCells


def load_market_offers(pDatabaseFile, pSince):
    """Retourne les offres du marché vues depuis pSince.

    Seules les offres en France comptent, hors stage, alternance et mission
    libre, comme pour le salaire du marché de chaque offre.
    """

    rOffers = [
        vOffer
        for vOffer in map(
            clean_missing_values,
            get_offers(
                pDatabaseFile, pCountry=FRANCE, pSeenSince=pSince, pHideIgnored=True
            ).to_dict("records"),
        )
        if vOffer.get("contract") not in EXCLUDED_CONTRACTS and not is_training(vOffer)
    ]

    return rOffers


def find_priority_skills(pSkills, pLevels):
    """Retourne les compétences les plus demandées que le profil maîtrise peu.

    Une compétence non évaluée, ou notée sous KNOWN_LEVEL, est à travailler.
    """

    rPriorities = [
        {
            "name": vName,
            "count": len(vSalaries),
            "level": pLevels.get(vName) or None,
            "label": f"{len(vSalaries)} offre(s) · "
            + (
                f"niveau {pLevels[vName]}/{MAX_LEVEL}"
                if pLevels.get(vName)
                else "non évaluée"
            ),
        }
        for vName, vSalaries in sorted(
            pSkills.items(), key=lambda pItem: (-len(pItem[1]), pItem[0])
        )
        if (pLevels.get(vName) or 0) < KNOWN_LEVEL
    ][:MAX_PRIORITY_SKILLS]

    return rPriorities


def build_market_history(pDatabaseFile, pNow, pMonths=HISTORY_MONTHS):
    """Retourne, mois par mois, les offres vues, celles qui citent une compétence du
    profil et leur net mensuel médian.
    """

    vSkills = set(load_profile(pDatabaseFile)["skills"])
    vMonths = {}
    vMonth = pNow.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    for _ in range(pMonths):
        vMonths[vMonth.strftime("%Y-%m")] = {"offers": 0, "mine": 0, "salaries": []}
        vSince = vMonth
        vMonth = (vMonth - timedelta(days=1)).replace(day=1)

    for vOffer in load_market_offers(pDatabaseFile, vSince):
        vKey = str(vOffer.get("first_seen_at") or "")[:7]

        if vKey not in vMonths:
            continue

        vMonths[vKey]["offers"] += 1
        vMonths[vKey]["mine"] += bool(vSkills & set(get_offer_skills(vOffer)))

        if (vSalary := get_net_salary(vOffer)) is not None:
            vMonths[vKey]["salaries"].append(vSalary)

    vKeys = sorted(vMonths)

    # Les mois vides du début sont retirés : une base récente ne montrerait
    # sinon que des mois sans offre. Le mois en cours reste.
    while len(vKeys) > 1 and not vMonths[vKeys[0]]["offers"]:
        vKeys.pop(0)

    rHistory = [
        {
            "month": vKey,
            "label": f"{MONTH_NAMES[int(vKey[5:]) - 1]} {vKey[:4]}",
            "offers": vMonths[vKey]["offers"],
            "mine": vMonths[vKey]["mine"],
            "median": summarize_salaries(vMonths[vKey]["salaries"]),
        }
        for vKey in vKeys
    ]

    return rHistory


def build_history_cells(pMonth):
    """Retourne les textes d'une ligne de l'évolution du marché."""

    rCells = [
        pMonth["label"],
        str(pMonth["offers"]),
        str(pMonth["mine"]),
        pMonth["median"],
    ]

    return rCells


def build_market(pDatabaseFile, pNow, pDays=MARKET_DAYS):
    """Retourne la synthèse du marché des pDays derniers jours : offres,
    salaires, compétences, régions et villes.
    """

    vOffers = load_market_offers(pDatabaseFile, pNow - timedelta(days=pDays))

    vSkills = {}
    vCities = {}
    vRegions = {}
    vSalaries = []

    for vOffer in vOffers:
        vSalary = get_net_salary(vOffer)

        if vSalary is not None:
            vSalaries.append(vSalary)

        for vSkill in get_offer_skills(vOffer):
            vSkills.setdefault(vSkill, []).append(vSalary)

        # Sans ville, l'offre compte dans le total mais pas dans le classement.
        if vOffer.get("city"):
            vCities.setdefault(vOffer["city"], []).append(vSalary)

        # Région connue une fois l'offre placée sur la carte (job/geocoding.py),
        # sinon nommée dans le lieu : « Pas-de-Calais, Hauts-de-France ».
        vRegion = find_region(vOffer.get("french_department")) or find_region_in_text(
            vOffer.get("location")
        )

        if vRegion:
            vRegions.setdefault(vRegion, []).append(vSalary)

    vProfile = load_profile(pDatabaseFile)
    vTarget = load_settings(pDatabaseFile)["target_net_salary"]

    rMarket = {
        "days": pDays,
        "offer_count": len(vOffers),
        "salaried_count": len(vSalaries),
        "unknown_city_count": len(vOffers) - sum(map(len, vCities.values())),
        "unknown_region_count": len(vOffers) - sum(map(len, vRegions.values())),
        "median": summarize_salaries(vSalaries),
        "target": format_euros(vTarget) if vTarget else None,
        "skills": build_rows(
            vSkills, len(vOffers), MAX_SKILL_ROWS, frozenset(vProfile["skills"])
        ),
        "cities": build_rows(vCities, len(vOffers), MAX_CITY_ROWS),
        "regions": build_rows(vRegions, len(vOffers), MAX_REGION_ROWS),
        "priorities": find_priority_skills(vSkills, vProfile.get("skill_levels") or {}),
    }

    logger.info(
        "Marché calculé : %s offre(s), %s avec salaire, %s compétence(s)",
        rMarket["offer_count"],
        rMarket["salaried_count"],
        len(vSkills),
    )

    return rMarket
