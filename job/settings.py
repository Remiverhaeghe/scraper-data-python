"""Réglages de calcul modifiables depuis l'interface de bureau et le web"""

from dataclasses import dataclass

from config import (
    CHALLENGE_WAIT_SECONDS,
    EXPIRY_DAYS,
    FOLLOW_UP_DAYS,
    NET_SALARY_RATIO,
    NEW_OFFER_DAYS,
)
from job.exchange_rates import load_stored_rates
from job.salary import add_net_salary, get_income_tax_rate
from storage.job_offers import get_salaries, update_net_salaries
from storage.settings_repository import get_setting_values, save_setting_values
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class SettingDefinition:
    """Description d'un réglage : libellé, aide, bornes et unité."""

    label: str
    help: str
    minimum: float
    maximum: float
    step: float
    unit: str
    is_integer: bool = True


SETTING_DEFINITIONS = {
    "net_salary_percent": SettingDefinition(
        "Salaire net",
        "Part du brut conservée après cotisations. 75 % est l'hypothèse prudente.",
        50,
        100,
        1,
        "% du brut",
    ),
    "income_tax_rate": SettingDefinition(
        "Impôt sur le revenu",
        "Taux de prélèvement à la source. 0 % pour ne pas le déduire.",
        0,
        60,
        0.1,
        "%",
        False,
    ),
    "new_offer_days": SettingDefinition(
        "Nouvelle offre",
        "Durée pendant laquelle une offre découverte est signalée comme nouvelle.",
        1,
        30,
        1,
        "jours",
    ),
    "expiry_days": SettingDefinition(
        "Offre expirée",
        "Une offre absente des recherches depuis ce délai est probablement expirée.",
        7,
        180,
        1,
        "jours",
    ),
    "follow_up_days": SettingDefinition(
        "Relance",
        "Délai proposé entre l'envoi d'une candidature et sa relance.",
        1,
        60,
        1,
        "jours",
    ),
    # Jamais nulle : sans attente, on trouverait la réponse par essais successifs.
    "challenge_wait_seconds": SettingDefinition(
        "Attente des défis",
        "Délai imposé après une réponse fausse avant un nouvel essai.",
        5,
        600,
        5,
        "s",
    ),
    "weekly_application_goal": SettingDefinition(
        "Objectif de la semaine",
        "Candidatures à envoyer chaque semaine, suivies sur l'accueil. 0 : aucun.",
        0,
        50,
        1,
        "candidatures",
    ),
    "archive_after_days": SettingDefinition(
        "Archivage",
        "Offres absentes des recherches depuis ce délai supprimées chaque jour, "
        "après une sauvegarde ; les offres suivies sont gardées. 0 : jamais.",
        0,
        3650,
        1,
        "jours",
    ),
    "target_net_salary": SettingDefinition(
        "Salaire visé",
        "Net mensuel souhaité, comparé au salaire des offres proches. 0 : aucun.",
        0,
        20000,
        50,
        "€ net/mois",
    ),
    "commute_cost_per_km": SettingDefinition(
        "Coût du trajet",
        "Coût d'un kilomètre en voiture (carburant, usure), déduit du net pour "
        "comparer les offres. 0 : non calculé.",
        0,
        2,
        0.05,
        "€/km",
        False,
    ),
    "experience_years": SettingDefinition(
        "Expérience",
        "Vos années d'expérience professionnelle, comparées à celles demandées "
        "par les offres. 0 : non renseignée.",
        0,
        50,
        1,
        "ans",
    ),
    "daily_digest_hour": SettingDefinition(
        "Récapitulatif quotidien",
        "Heure d'envoi du récapitulatif du jour par e-mail : offres, relances, "
        "entretiens du lendemain. 0 : désactivé.",
        0,
        23,
        1,
        "h",
    ),
    "weight_match": SettingDefinition(
        "Score global : profil",
        "Poids de la correspondance au profil dans le score global. 0 : ignorée.",
        0,
        10,
        1,
        "poids",
    ),
    "weight_distance": SettingDefinition(
        "Score global : distance",
        "Poids de la proximité du domicile (télétravail compris). 0 : ignorée.",
        0,
        10,
        1,
        "poids",
    ),
    "weight_salary": SettingDefinition(
        "Score global : salaire",
        "Poids du salaire comparé au salaire visé. 0 : ignoré.",
        0,
        10,
        1,
        "poids",
    ),
    "weight_freshness": SettingDefinition(
        "Score global : fraîcheur",
        "Poids de la fraîcheur de l'annonce. 0 : ignorée.",
        0,
        10,
        1,
        "poids",
    ),
    "weight_employer": SettingDefinition(
        "Score global : employeur",
        "Poids du type d'employeur : client final, ESN, intérim. 0 : ignoré.",
        0,
        10,
        1,
        "poids",
    ),
}

# Réglages dont la modification change le net des offres déjà enregistrées
SALARY_SETTINGS = ("net_salary_percent", "income_tax_rate")


def get_default_settings():
    """Retourne les réglages par défaut ; l'impôt reprend INCOME_TAX_RATE s'il existe."""

    try:
        vTaxRate = get_income_tax_rate() or 0

    except ValueError as vException:
        logger.warning("INCOME_TAX_RATE ignoré : %s", vException)

        vTaxRate = 0

    rSettings = {
        "net_salary_percent": round(NET_SALARY_RATIO * 100),
        "income_tax_rate": vTaxRate,
        "new_offer_days": NEW_OFFER_DAYS,
        "expiry_days": EXPIRY_DAYS,
        "follow_up_days": FOLLOW_UP_DAYS,
        "challenge_wait_seconds": CHALLENGE_WAIT_SECONDS,
        "weekly_application_goal": 0,
        "target_net_salary": 0,
        "archive_after_days": 0,
        "commute_cost_per_km": 0.25,
        "experience_years": 0,
        "daily_digest_hour": 0,
        "weight_match": 5,
        "weight_distance": 3,
        "weight_salary": 2,
        "weight_freshness": 2,
        "weight_employer": 1,
    }

    return rSettings


def parse_setting(pKey, pValue):
    """Convertit une saisie en nombre et vérifie ses bornes."""

    vDefinition = SETTING_DEFINITIONS[pKey]

    try:
        vValue = float(str(pValue).strip().replace(",", "."))

    except ValueError:
        raise ValueError(f"{vDefinition.label} : nombre attendu") from None

    if not vDefinition.minimum <= vValue <= vDefinition.maximum:
        raise ValueError(
            f"{vDefinition.label} : valeur attendue entre "
            f"{vDefinition.minimum:g} et {vDefinition.maximum:g} {vDefinition.unit}"
        )

    if vDefinition.is_integer and not vValue.is_integer():
        raise ValueError(f"{vDefinition.label} : nombre entier attendu")

    rValue = int(vValue) if vDefinition.is_integer else vValue

    return rValue


def load_settings(pDatabaseFile):
    """Retourne les réglages enregistrés, complétés par les valeurs par défaut."""

    vSettings = get_default_settings()

    for vKey, vValue in get_setting_values(pDatabaseFile).items():
        # app_setting contient aussi la planification et l'adresse e-mail
        # (job/schedule.py) : seules les clés des règles de calcul sont lues ici.
        if vKey in SETTING_DEFINITIONS:
            try:
                vSettings[vKey] = parse_setting(vKey, vValue)

            except ValueError as vException:
                logger.warning("Réglage enregistré ignoré : %s", vException)

    rSettings = vSettings

    return rSettings


def get_net_ratio(pSettings):
    """Retourne le ratio brut / net à appliquer."""

    rRatio = pSettings["net_salary_percent"] / 100

    return rRatio


def get_tax_rate(pSettings):
    """Retourne le taux d'imposition, ou None s'il ne doit pas être déduit."""

    rRate = pSettings["income_tax_rate"] or None

    return rRate


def recompute_net_salaries(pDatabaseFile, pSettings):
    """Recalcule le net des offres en base à partir de leur brut ; retourne leur nombre."""

    vSalaries = get_salaries(pDatabaseFile)

    # Taux déjà enregistrés seulement : modifier une règle n'attend pas le réseau.
    vSalaries = add_net_salary(
        vSalaries,
        pNetRatio=get_net_ratio(pSettings),
        pTaxRate=get_tax_rate(pSettings),
        pRates=load_stored_rates(pDatabaseFile)[0],
    )

    rCount = update_net_salaries(pDatabaseFile, vSalaries)

    logger.info("Salaire net recalculé pour %s offre(s)", rCount)

    return rCount


def save_settings(pDatabaseFile, pValues):
    """Valide puis enregistre les réglages ; retourne les réglages et les offres recalculées.

    Aucun réglage n'est enregistré si l'un d'eux est invalide : les erreurs sont
    toutes signalées ensemble.
    """

    vCurrent = load_settings(pDatabaseFile)
    vSettings = dict(vCurrent)
    vErrors = []

    for vKey in SETTING_DEFINITIONS:
        if vKey in pValues:
            try:
                vSettings[vKey] = parse_setting(vKey, pValues[vKey])

            except ValueError as vException:
                vErrors.append(str(vException))

    if vErrors:
        raise ValueError(". ".join(vErrors))

    save_setting_values(pDatabaseFile, vSettings)

    logger.info("Réglages enregistrés : %s", vSettings)

    vRecomputed = 0

    if any(vSettings[vKey] != vCurrent[vKey] for vKey in SALARY_SETTINGS):
        vRecomputed = recompute_net_salaries(pDatabaseFile, vSettings)

    rResult = (vSettings, vRecomputed)

    return rResult
