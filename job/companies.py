"""Entreprises à exclure ou à privilégier, et candidatures déjà envoyées"""

import json

from job.fingerprint import normalize_company
from job.presentation import STATUS_LABELS, format_date
from storage.job_applications import get_company_applications
from storage.job_offers import get_offers
from storage.settings_repository import get_setting_values, save_setting_values
from utils.logger import get_logger

logger = get_logger(__name__)

COMPANY_RULES_KEY = "company_rules"

COMPANY_RULE_KINDS = {"excluded": "à exclure", "preferred": "à privilégier"}

MAX_COMPANIES = 200
MAX_COMPANY_LENGTH = 200

# Candidatures citées dans l'avertissement, les autres sont seulement comptées
MAX_LISTED_APPLICATIONS = 3

# Offres des entreprises privilégiées montrées sur l'accueil
PREFERRED_OFFERS_LIMIT = 10


def parse_companies(pText):
    """Découpe une liste saisie, une entreprise par ligne ou séparée par des virgules."""

    rCompanies = []
    vKeys = set()

    for vLine in str(pText or "").replace(",", "\n").splitlines():
        vName = " ".join(vLine.split())
        vKey = normalize_company(vName)

        # Les doublons à la casse ou à la forme juridique près sont ignorés.
        if vKey and vKey not in vKeys:
            if len(vName) > MAX_COMPANY_LENGTH:
                raise ValueError(
                    f"Nom d'entreprise trop long : {MAX_COMPANY_LENGTH} caractères "
                    "au maximum."
                )

            vKeys.add(vKey)
            rCompanies.append(vName)

    if len(rCompanies) > MAX_COMPANIES:
        raise ValueError(f"{MAX_COMPANIES} entreprises au maximum par liste.")

    return rCompanies


def load_company_rules(pDatabaseFile):
    """Retourne les entreprises à exclure et à privilégier."""

    rRules = {vKind: [] for vKind in COMPANY_RULE_KINDS}

    vValue = get_setting_values(pDatabaseFile).get(COMPANY_RULES_KEY)

    if vValue:
        try:
            vStored = json.loads(vValue)
            rRules.update(
                {vKind: list(vStored.get(vKind, [])) for vKind in COMPANY_RULE_KINDS}
            )

        except (ValueError, AttributeError):
            logger.warning("Listes d'entreprises enregistrées illisibles, ignorées")

    return rRules


def save_company_rules(pDatabaseFile, pExcludedText, pPreferredText):
    """Valide puis enregistre les deux listes ; retourne les listes enregistrées."""

    rRules = {
        "excluded": parse_companies(pExcludedText),
        "preferred": parse_companies(pPreferredText),
    }

    vBoth = {normalize_company(vName) for vName in rRules["excluded"]} & {
        normalize_company(vName) for vName in rRules["preferred"]
    }

    if vBoth:
        raise ValueError(
            "Une entreprise ne peut pas être à la fois exclue et privilégiée : "
            + ", ".join(sorted(vBoth))
            + "."
        )

    save_setting_values(
        pDatabaseFile, {COMPANY_RULES_KEY: json.dumps(rRules, ensure_ascii=False)}
    )

    logger.info(
        "Entreprises enregistrées : %s exclue(s), %s privilégiée(s)",
        len(rRules["excluded"]),
        len(rRules["preferred"]),
    )

    return rRules


def add_company_rule(pDatabaseFile, pCompany, pKind):
    """Ajoute une entreprise à une liste et la retire de l'autre ; retourne les listes."""

    if pKind not in COMPANY_RULE_KINDS:
        raise ValueError("Liste d'entreprises inconnue.")

    vKey = normalize_company(pCompany)

    if not vKey:
        raise ValueError("Cette offre n'indique pas d'entreprise.")

    vRules = load_company_rules(pDatabaseFile)

    vLists = {
        vKind: [vName for vName in vNames if normalize_company(vName) != vKey]
        for vKind, vNames in vRules.items()
    }
    vLists[pKind].append(" ".join(str(pCompany).split()))

    rRules = save_company_rules(
        pDatabaseFile, "\n".join(vLists["excluded"]), "\n".join(vLists["preferred"])
    )

    return rRules


def get_company_keys(pRules, pKind):
    """Retourne les noms normalisés d'une liste, tels que cherchés en base."""

    rKeys = [normalize_company(vName) for vName in pRules[pKind]]

    return rKeys


def get_company_rule(pCompany, pRules):
    """Retourne « excluded », « preferred » ou None pour l'entreprise d'une offre."""

    vKey = normalize_company(pCompany)

    rKind = next(
        (
            vKind
            for vKind in COMPANY_RULE_KINDS
            if vKey and vKey in get_company_keys(pRules, vKind)
        ),
        None,
    )

    return rKind


def mark_preferred_companies(pOffers, pRules):
    """Signale dans chaque offre si son entreprise est privilégiée, pour l'affichage."""

    vKeys = set(get_company_keys(pRules, "preferred"))

    for vOffer in pOffers:
        vOffer["company_preferred"] = normalize_company(vOffer.get("company")) in vKeys


def find_preferred_offers(pDatabaseFile, pSince, pLimit=PREFERRED_OFFERS_LIMIT):
    """Retourne les offres récentes des entreprises privilégiées, les plus récentes
    en tête : la liste des entreprises privilégiées sert de veille.
    """

    vKeys = set(get_company_keys(load_company_rules(pDatabaseFile), "preferred"))

    if not vKeys:
        return []

    rOffers = [
        vOffer
        for vOffer in get_offers(
            pDatabaseFile, pSeenSince=pSince, pHideIgnored=True
        ).to_dict("records")
        if normalize_company(vOffer.get("company")) in vKeys
    ][:pLimit]

    return rOffers


def find_company_applications(pDatabaseFile, pOffer):
    """Retourne les autres candidatures envoyées à l'entreprise de l'offre."""

    vKey = normalize_company(pOffer.get("company"))

    rApplications = (
        get_company_applications(
            pDatabaseFile, vKey, (pOffer["source"], str(pOffer["source_id"]))
        )
        if vKey
        else []
    )

    return rApplications


def find_company_contacts(pApplications):
    """Retourne les adresses de recruteurs connues, sans doublon, récentes en tête."""

    rContacts = list(
        dict.fromkeys(
            vApplication["contact_email"]
            for vApplication in pApplications
            if vApplication.get("contact_email")
        )
    )

    return rContacts


def describe_company_applications(pApplications):
    """Résume les candidatures déjà envoyées à l'entreprise, ou None s'il n'y en a pas."""

    rText = None

    if pApplications:
        vItems = [
            f"{vApplication['title'] or 'offre sans titre'} "
            f"({STATUS_LABELS.get(vApplication['status'], vApplication['status'])}"
            + (
                f", le {format_date(vApplication['applied_at'])}"
                if vApplication["applied_at"]
                else ""
            )
            + ")"
            for vApplication in pApplications[:MAX_LISTED_APPLICATIONS]
        ]

        if len(pApplications) > MAX_LISTED_APPLICATIONS:
            vItems.append(f"et {len(pApplications) - MAX_LISTED_APPLICATIONS} autre(s)")

        vContacts = find_company_contacts(pApplications)

        rText = (
            f"Déjà {len(pApplications)} candidature(s) dans cette entreprise : "
            + ", ".join(vItems)
            + (f". Contact connu : {', '.join(vContacts)}" if vContacts else "")
        )

    return rText


def build_company_filter_keys(pRules):
    """Retourne les noms normalisés des deux listes, attendus par build_offer_filters."""

    rKeys = {vKind: get_company_keys(pRules, vKind) for vKind in COMPANY_RULE_KINDS}

    return rKeys
