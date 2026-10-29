"""Salaire du marché : net mensuel des offres proches, comparé au salaire visé

Une offre se compare aux offres en France qui annoncent un salaire, de même
nature (emploi, ou bien stage et alternance) et qui partagent au moins deux de
ses compétences ; l'intitulé, trop variable d'une annonce à l'autre, ne compte
pas. En dessous de MIN_COMPARABLES offres, aucune médiane n'est donnée.
"""

import re
from statistics import median, quantiles

from job.geocoding import ROAD_DETOUR_FACTOR
from job.location import FRANCE
from job.preparation import get_offer_skills
from job.presentation import clean_missing_values, format_euros
from job.settings import get_net_ratio, get_tax_rate, load_settings
from storage.job_offers import get_offers, get_salary_signature

MIN_COMPARABLES = 3
MIN_SKILL_SHARE = 1 / 3
MIN_SHARED_SKILLS = 2

# Un tarif de mission n'est pas un salaire : le freelance est écarté.
EXCLUDED_CONTRACTS = ("FREELANCE",)

# Stage et alternance ne se comparent qu'entre eux.
TRAINING_PATTERN = re.compile(
    r"\b(?:stages?|stagiaires?|alternan\w*|apprenti\w*|intern(?:ship)?|trainee)\b",
    re.IGNORECASE,
)

# Écart au-delà duquel le salaire visé est dit au-dessus ou en dessous du marché
TARGET_MARGIN = 0.05


# Jours de trajet par mois, et part sur site d'une offre en télétravail
COMMUTE_WORKDAYS = 21
HYBRID_ONSITE_SHARE = 0.6


def get_net_salary(pOffer):
    """Retourne le net mensuel d'une offre : milieu de sa fourchette, ou None."""

    vValues = [
        vValue
        for vValue in (
            pOffer.get("salary_net_monthly_min"),
            pOffer.get("salary_net_monthly_max"),
        )
        if vValue is not None
    ]

    rSalary = sum(vValues) / len(vValues) if vValues else None

    return rSalary


def is_training(pOffer):
    """Indique si l'offre est un stage ou une alternance, d'après son intitulé."""

    rTraining = bool(TRAINING_PATTERN.search(str(pOffer.get("title") or "")))

    return rTraining


def share_skills(pFirst, pSecond):
    """Indique si deux offres partagent assez de compétences pour être comparées."""

    vCommon = len(pFirst & pSecond)

    rShared = (
        vCommon >= MIN_SHARED_SKILLS
        and vCommon / len(pFirst | pSecond) >= MIN_SKILL_SHARE
    )

    return rShared


# Offres avec salaire, gardées tant que les offres et les nets ne changent pas :
# Offres, fiche d'une offre et annonces douteuses les relisent à chaque affichage.
SALARIED_CACHE = {}


def load_salaried_offers(pDatabaseFile):
    """Retourne les offres comparables lues une fois : (offre, compétences, net)."""

    vKey = (str(pDatabaseFile), get_salary_signature(pDatabaseFile))

    if vKey not in SALARIED_CACHE:
        SALARIED_CACHE.clear()
        SALARIED_CACHE[vKey] = read_salaried_offers(pDatabaseFile)

    rOffers = SALARIED_CACHE[vKey]

    return rOffers


def read_salaried_offers(pDatabaseFile):
    """Lit en base les offres comparables : (offre, compétences, net)."""

    rOffers = [
        (vOffer, set(get_offer_skills(vOffer)), vSalary)
        for vOffer in map(
            clean_missing_values,
            get_offers(pDatabaseFile, pCountry=FRANCE, pHasSalary=True).to_dict(
                "records"
            ),
        )
        if vOffer.get("contract") not in EXCLUDED_CONTRACTS
        and (vSalary := get_net_salary(vOffer)) is not None
    ]

    return rOffers


def collect_salaries(pOffer, pSalaried):
    """Retourne le net des offres comparables à pOffer, elle-même exclue."""

    vSkills = set(get_offer_skills(pOffer))
    vKey = (pOffer.get("source"), str(pOffer.get("source_id")))
    vTraining = is_training(pOffer)

    rSalaries = (
        [
            vSalary
            for vOtherKey, vOtherTraining, vOtherSkills, vSalary in get_comparables(
                pSalaried
            )
            if vOtherKey != vKey
            and vOtherTraining == vTraining
            and share_skills(vSkills, vOtherSkills)
        ]
        if vSkills
        else []
    )

    return rSalaries


# Clé et stage repérés une fois par liste d'offres salariées, pas à chaque offre
COMPARABLES_CACHE = {}


def get_comparables(pSalaried):
    """Retourne (clé, stage, compétences, net) pour chaque offre salariée."""

    vKey = id(pSalaried)
    vCached = COMPARABLES_CACHE.get(vKey)

    if vCached is None or vCached[0] is not pSalaried:
        vCached = (
            pSalaried,
            [
                (
                    (vOther["source"], str(vOther["source_id"])),
                    is_training(vOther),
                    vSkills,
                    vSalary,
                )
                for vOther, vSkills, vSalary in pSalaried
            ],
        )
        COMPARABLES_CACHE.clear()
        COMPARABLES_CACHE[vKey] = vCached

    rComparables = vCached[1]

    return rComparables


def add_estimated_salaries(pDatabaseFile, pOffers):
    """Donne aux offres en France sans salaire la médiane des offres comparables.

    estimated_salary, mis en forme, n'est donné qu'à partir de MIN_COMPARABLES
    salaires : c'est une estimation, affichée comme telle.
    """

    vSalaried = None

    for vOffer in pOffers:
        vOffer["estimated_salary"] = None

        if vOffer.get("country") != FRANCE or get_net_salary(vOffer) is not None:
            continue

        # Lecture faite une fois, et seulement si une offre en a besoin
        if vSalaried is None:
            vSalaried = load_salaried_offers(pDatabaseFile)

        vSalaries = collect_salaries(vOffer, vSalaried)

        if len(vSalaries) >= MIN_COMPARABLES:
            vOffer["estimated_salary"] = format_euros(median(vSalaries))


def find_market_salary(pDatabaseFile, pOffer):
    """Retourne la médiane, l'écart interquartile et le nombre d'offres proches.

    Retourne None si moins de MIN_COMPARABLES offres comparables ont un salaire.
    """

    if not get_offer_skills(pOffer):
        return None

    vSalaries = collect_salaries(pOffer, load_salaried_offers(pDatabaseFile))

    if len(vSalaries) < MIN_COMPARABLES:
        return None

    vLow, _, vHigh = quantiles(vSalaries, n=4)
    vTarget = load_settings(pDatabaseFile)["target_net_salary"] or None

    rMarket = {
        "median": median(vSalaries),
        "low": vLow,
        "high": vHigh,
        "count": len(vSalaries),
        "target": vTarget,
    }

    return rMarket


def to_gross_yearly(pNetMonthly, pSettings):
    """Retourne le brut annuel d'un net mensuel, arrondi à la centaine.

    Calcul inverse de job/salary.py, avec les règles des Paramètres : c'est en
    brut annuel que se discute un salaire en entretien.
    """

    vTaxShare = 1 - (get_tax_rate(pSettings) or 0) / 100

    rGross = round(pNetMonthly / get_net_ratio(pSettings) / vTaxShare * 12, -2)

    return rGross


def describe_negotiation(pMarket, pOffer, pSettings):
    """Retourne un argumentaire de négociation d'après le marché, ou un texte vide.

    La demande proposée est le salaire visé, ou la médiane du marché s'il est
    en dessous : le marché le justifie.
    """

    if pMarket is None:
        return ""

    vAsk = max(pMarket["target"] or 0, pMarket["median"])

    vLow = format_euros(to_gross_yearly(pMarket["low"], pSettings))
    vHigh = format_euros(to_gross_yearly(pMarket["high"], pSettings))

    vParts = [
        "Offres proches : "
        + (f"{vLow} à {vHigh}" if vLow != vHigh else vLow)
        + " brut annuel",
        f"demande appuyée par le marché : {format_euros(to_gross_yearly(vAsk, pSettings))} "
        "brut annuel",
    ]

    vOffered = get_net_salary(pOffer)

    if vOffered is not None:
        vGap = (vOffered - pMarket["median"]) / pMarket["median"]
        vParts.append(
            "l'offre annonce "
            + (
                "plus que le marché"
                if vGap > TARGET_MARGIN
                else (
                    "moins que le marché"
                    if vGap < -TARGET_MARGIN
                    else "le prix du marché"
                )
            )
        )

    rText = " · ".join(vParts)

    return rText


def describe_market_salary(pMarket):
    """Résume le salaire du marché en une ligne, salaire visé compris."""

    if pMarket is None:
        return (
            "Pas encore assez d'offres proches avec un salaire : la comparaison "
            "s'affine à chaque recherche"
        )

    rText = (
        f"{format_euros(pMarket['median'])} net médian sur {pMarket['count']} offres "
        f"proches ({format_euros(pMarket['low'])} – {format_euros(pMarket['high'])})"
    )

    vTarget = pMarket["target"]

    if vTarget:
        vGap = (vTarget - pMarket["median"]) / pMarket["median"]

        if vGap > TARGET_MARGIN:
            vPosition = "au-dessus du marché"
        elif vGap < -TARGET_MARGIN:
            vPosition = "en dessous du marché"
        else:
            vPosition = "dans le marché"

        rText += f" · visé {format_euros(vTarget)} : {vPosition}"

    return rText


def describe_net_after_commute(pOffer, pSettings):
    """Retourne le net mensuel diminué du trajet en voiture, ou un texte vide.

    Le trajet compte deux fois la route par jour sur site ; une offre en
    télétravail est supposée hybride, faute de rythme précisé.
    """

    vNet = get_net_salary(pOffer)
    vDistance = pOffer.get("distance_km")
    vCostPerKm = pSettings["commute_cost_per_km"]

    if vNet is None or vDistance is None or not vCostPerKm:
        return ""

    vDays = COMMUTE_WORKDAYS * (HYBRID_ONSITE_SHARE if pOffer.get("remote") else 1)
    vCost = 2 * vDistance * ROAD_DETOUR_FACTOR * vDays * vCostPerKm

    rText = (
        f"{format_euros(vNet - vCost)} après trajet : environ "
        f"{format_euros(vCost)} par mois pour {vDistance} km à vol d'oiseau"
        + (", 3 jours sur site par semaine" if pOffer.get("remote") else "")
    )

    return rText
