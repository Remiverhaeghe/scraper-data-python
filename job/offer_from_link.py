"""Offre créée depuis le lien d'une annonce, lue dans sa fiche structurée

La plupart des sites d'emploi décrivent leurs annonces au format schema.org
JobPosting, dans un bloc JSON-LD destiné aux moteurs de recherche : titre,
entreprise, lieu, description, contrat et salaire y sont lus sans deviner.
"""

import json
import re

import requests

from job.manual_offers import add_manual_offer
from utils.api_client import request_bytes
from utils.helpers import html_to_text
from utils.logger import get_logger

logger = get_logger(__name__)

JSON_LD_PATTERN = re.compile(
    r"<script[^>]+type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>",
    re.IGNORECASE | re.DOTALL,
)

HEADERS = {
    "Accept": "text/html,application/xhtml+xml",
    "User-Agent": "JobBoardPerso/1.0 (usage personnel)",
}

# Type de contrat schema.org vers celui de l'application ; les autres (temps
# plein, stage…) ne disent pas CDI ou CDD et restent vides.
CONTRACTS = {"CONTRACTOR": "FREELANCE", "TEMPORARY": "CDD"}


def find_job_posting(pHtml):
    """Retourne la première fiche JobPosting de la page, ou None."""

    vCandidates = []

    for vBlock in JSON_LD_PATTERN.findall(pHtml):
        try:
            vData = json.loads(vBlock, strict=False)

        except ValueError:
            continue

        vCandidates += vData if isinstance(vData, list) else [vData]

    while vCandidates:
        vItem = vCandidates.pop(0)

        if not isinstance(vItem, dict):
            continue

        vType = vItem.get("@type")

        if vType == "JobPosting" or (isinstance(vType, list) and "JobPosting" in vType):
            return vItem

        vCandidates += vItem.get("@graph") or []

    return None


def first_item(pValue):
    """Retourne le premier élément d'une liste, ou la valeur elle-même."""

    rItem = pValue[0] if isinstance(pValue, list) and pValue else pValue

    return rItem if isinstance(rItem, dict) else {}


def describe_salary(pSalary):
    """Retourne le salaire annoncé en texte, tel qu'écrit par la source, ou None."""

    vSalary = first_item(pSalary)
    vValue = first_item(vSalary.get("value")) or {}
    vAmounts = [
        str(vAmount)
        for vAmount in (
            vValue.get("minValue"),
            vValue.get("maxValue"),
            vValue.get("value"),
        )
        if vAmount
    ]

    rText = (
        f"{' - '.join(vAmounts)} {vSalary.get('currency') or ''} "
        f"{(vValue.get('unitText') or '').lower()}".strip()
        if vAmounts
        else None
    )

    return rText


def read_job_posting(pPosting, pUrl):
    """Traduit une fiche JobPosting en champs d'offre saisie."""

    vAddress = first_item(first_item(pPosting.get("jobLocation")).get("address"))
    vContract = first_item([pPosting.get("employmentType")]) or pPosting.get(
        "employmentType"
    )

    rFields = {
        "title": pPosting.get("title"),
        "company": first_item(pPosting.get("hiringOrganization")).get("name"),
        "url": pPosting.get("url") or pUrl,
        "description": html_to_text(pPosting.get("description")),
        "location": " ".join(
            vPart
            for vPart in (vAddress.get("postalCode"), vAddress.get("addressLocality"))
            if vPart
        )
        or None,
        "contract": CONTRACTS.get(str(vContract).upper()),
        "salary_label": describe_salary(pPosting.get("baseSalary")),
        "remote": "oui" if pPosting.get("jobLocationType") == "TELECOMMUTE" else None,
    }

    return rFields


def fetch_offer_fields(pUrl):
    """Lit la page de l'annonce et retourne ses champs ; lève ValueError sinon."""

    try:
        vHtml = request_bytes(
            "GET", pUrl, pHeaders=HEADERS, pExpectedType="html"
        ).decode("utf-8", "replace")

    except requests.RequestException as vException:
        logger.warning("Annonce illisible depuis le lien : %s", vException)
        raise ValueError(
            "Page inaccessible : le site refuse peut-être les lectures "
            "automatiques. Utilisez la saisie manuelle."
        ) from vException

    vPosting = find_job_posting(vHtml)

    if vPosting is None:
        raise ValueError(
            "Aucune fiche d'offre structurée sur cette page : utilisez la saisie "
            "manuelle."
        )

    rFields = read_job_posting(vPosting, pUrl)

    return rFields


def add_offer_from_link(pDatabaseFile, pUrl, pNow):
    """Crée l'offre décrite par la page du lien ; retourne son identifiant."""

    rSourceId = add_manual_offer(pDatabaseFile, fetch_offer_fields(pUrl), pNow)

    logger.info("Offre créée depuis un lien : %s", rSourceId)

    return rSourceId
