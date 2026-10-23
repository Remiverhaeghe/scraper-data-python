"""Entreprises suivies sur les plateformes de pages carrière

Pour chaque plateforme : la liste réglée dans Paramètres (en base), sinon celle
du .env, sinon la liste par défaut vérifiée. « Vérifier » interroge l'API pour
dire, entreprise par entreprise, si elle publie des offres.
"""

import os
from pathlib import Path

import requests

import config
from storage.settings_repository import get_setting_values, save_setting_values
from utils.logger import get_logger

logger = get_logger(__name__)

# Plateforme : (libellé, variable .env, entreprises par défaut, adresse d'exemple)
PLATFORMS = {
    "smartrecruiters": (
        "SmartRecruiters",
        "SMARTRECRUITERS_COMPANIES",
        "Alten,Assystem,Eurofins,Loxam,Trigo,BoschGroup,SaintGobain,Ubisoft2,"
        "Kiabi,Lesaffre,Boulanger",
        "jobs.smartrecruiters.com/<identifiant>",
    ),
    "lever": (
        "Lever",
        "LEVER_COMPANIES",
        "qonto,aircall,swile,agicap,malt",
        "jobs.lever.co/<identifiant>",
    ),
    "ashby": (
        "Ashby",
        "ASHBY_COMPANIES",
        "alan,pennylane,ledger,photoroom,dust,lemlist,nabla",
        "jobs.ashbyhq.com/<identifiant>",
    ),
    "greenhouse": (
        "Greenhouse",
        "GREENHOUSE_BOARD",
        "",
        "boards.greenhouse.io/<identifiant>",
    ),
    "recruitee": (
        "Recruitee",
        "RECRUITEE_COMPANIES",
        "",
        "<identifiant>.recruitee.com",
    ),
    "workable": (
        "Workable",
        "WORKABLE_ACCOUNTS",
        "",
        "apply.workable.com/<compte>",
    ),
    # Grands groupes : [Nom=]hôte/tenant/site, lu dans l'adresse du site carrière
    "workday": (
        "Workday",
        "WORKDAY_SITES",
        "Valeo=valeo.wd3/valeo/valeo_jobs,Airbus=ag.wd3/ag/Airbus,"
        "LFB=lfb.wd3/lfb/LFB_External_Careers,Néosoft=neosoft.wd3/neosoft/neo-soft",
        "<hôte>.myworkdayjobs.com/<site> : hôte/tenant/site",
    ),
}

SETTING_PREFIX = "company_pages/"


def split_companies(pValue):
    """Retourne les identifiants d'une liste séparée par des virgules ou des lignes."""

    rCompanies = [
        vName.strip()
        for vName in str(pValue or "").replace("\n", ",").split(",")
        if vName.strip()
    ]

    return rCompanies


def load_company_list(pPlatform, pDatabaseFile=None):
    """Retourne les entreprises suivies d'une plateforme, séparées par des virgules.

    Paramètres l'emporte sur le .env, qui l'emporte sur la liste par défaut. La
    base n'est lue que si elle existe : la lecture ne la crée jamais.
    """

    _, vSetting, vDefault, _ = PLATFORMS[pPlatform]
    vDatabaseFile = pDatabaseFile or config.DATABASE_FILE
    vSaved = None

    if Path(vDatabaseFile).exists():
        vSaved = get_setting_values(vDatabaseFile).get(SETTING_PREFIX + pPlatform)

    rCompanies = vSaved if vSaved is not None else (os.getenv(vSetting) or vDefault)

    return rCompanies


def save_company_lists(pDatabaseFile, pLists):
    """Enregistre les entreprises suivies, {plateforme: texte saisi}."""

    vValues = {
        SETTING_PREFIX + vPlatform: ",".join(split_companies(vText))
        for vPlatform, vText in pLists.items()
        if vPlatform in PLATFORMS
    }
    save_setting_values(pDatabaseFile, vValues)

    logger.info(
        "Pages carrière suivies : %s",
        ", ".join(
            f"{PLATFORMS[vPlatform][0]} {len(split_companies(vText))}"
            for vPlatform, vText in pLists.items()
            if vPlatform in PLATFORMS
        ),
    )


def count_published_offers(pPlatform, pCompany):
    """Retourne le nombre d'offres publiées par une entreprise sur une plateforme."""

    # Imports locaux : chaque plateforme n'est chargée que si elle est vérifiée.
    # pylint: disable=import-outside-toplevel
    if pPlatform == "smartrecruiters":
        from job.sources.smartrecruiters.client import get_postings
        from job.sources.smartrecruiters.config import load_config

        rCount = get_postings(pCompany, load_config().country).get("totalFound", 0)
    elif pPlatform == "lever":
        from job.sources.lever.client import get_postings

        rCount = len(get_postings(pCompany))
    elif pPlatform == "ashby":
        from job.sources.ashby.client import get_jobs

        rCount = len(get_jobs(pCompany))
    elif pPlatform == "greenhouse":
        from job.sources.greenhouse.client import get_jobs

        rCount = len(get_jobs(pCompany).get("jobs", []))
    elif pPlatform == "recruitee":
        from job.sources.recruitee.client import get_offers

        rCount = len(get_offers(pCompany))
    elif pPlatform == "workable":
        from job.sources.workable.client import get_account

        rCount = len(get_account(pCompany).get("jobs", []))
    else:
        from job.sources.workday.client import parse_site, search_jobs

        rCount = search_jobs(parse_site(pCompany), None, 0).get("total", 0)

    return rCount


def check_companies(pPlatform, pText):
    """Vérifie chaque entreprise saisie ; retourne [(identifiant, offres ou None, message)]."""

    rResults = []

    for vCompany in split_companies(pText):
        try:
            vCount = count_published_offers(pPlatform, vCompany)
            vMessage = (
                f"{vCount} offre(s)"
                if vCount
                else "aucune offre publiée pour le moment"
            )
        except (requests.RequestException, ValueError) as vException:
            # Un 404 signale le plus souvent un identifiant mal orthographié.
            logger.warning(
                "%s : entreprise %s injoignable : %s",
                PLATFORMS[pPlatform][0],
                vCompany,
                vException,
            )
            vCount = None
            vMessage = (
                f"introuvable, vérifier l'identifiant dans {PLATFORMS[pPlatform][3]}"
            )

        rResults.append((vCompany, vCount, vMessage))

    return rResults
