"""Mon marché : demande et salaires par compétence et par ville, d'après les offres"""

from datetime import timedelta
from statistics import median

from job.location import FRANCE
from job.preparation import get_offer_skills
from job.presentation import clean_missing_values, format_euros
from job.profile import load_profile
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

# Colonnes des tableaux, communes au bureau et au web
MARKET_COLUMNS = ["Offres", "Part", "Avec salaire", "Net mensuel médian"]
SKILL_COLUMNS = ["Compétence", *MARKET_COLUMNS, "Dans mon profil"]
CITY_COLUMNS = ["Ville", *MARKET_COLUMNS]


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


def build_market(pDatabaseFile, pNow, pDays=MARKET_DAYS):
    """Retourne la synthèse du marché : offres, salaires, compétences et villes.

    Seules les offres en France et en CDI, CDD ou intérim des pDays derniers
    jours comptent, hors stage, alternance et mission libre, comme le salaire
    du marché de chaque offre.
    """

    vOffers = [
        vOffer
        for vOffer in map(
            clean_missing_values,
            get_offers(
                pDatabaseFile,
                pCountry=FRANCE,
                pSeenSince=pNow - timedelta(days=pDays),
                pHideIgnored=True,
            ).to_dict("records"),
        )
        if vOffer.get("contract") not in EXCLUDED_CONTRACTS and not is_training(vOffer)
    ]

    vSkills = {}
    vCities = {}
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

    vProfile = load_profile(pDatabaseFile)
    vTarget = load_settings(pDatabaseFile)["target_net_salary"]

    rMarket = {
        "days": pDays,
        "offer_count": len(vOffers),
        "salaried_count": len(vSalaries),
        "unknown_city_count": len(vOffers) - sum(map(len, vCities.values())),
        "median": summarize_salaries(vSalaries),
        "target": format_euros(vTarget) if vTarget else None,
        "skills": build_rows(
            vSkills, len(vOffers), MAX_SKILL_ROWS, frozenset(vProfile["skills"])
        ),
        "cities": build_rows(vCities, len(vOffers), MAX_CITY_ROWS),
    }

    logger.info(
        "Marché calculé : %s offre(s), %s avec salaire, %s compétence(s)",
        rMarket["offer_count"],
        rMarket["salaried_count"],
        len(vSkills),
    )

    return rMarket
