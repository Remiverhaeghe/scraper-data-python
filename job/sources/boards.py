"""Sources sans recherche : pages carrière d'entreprises et flux d'offres

Lever, Ashby, Recruitee et Workable publient toutes les offres d'une entreprise
d'un seul appel ; Remote OK, Working Nomads et We Work Remotely, leurs offres
récentes. Aucune ne cherche côté serveur : le pays, le mot-clé et le lieu sont
filtrés ici, avant la limite.
"""

import os

import pandas as pd

from job.csv_schema import JOB_COLUMNS
from job.filter import filter_by_keyword_and_location
from job.sources.config import SourceDefinition, scrape_each
from utils.logger import get_logger

logger = get_logger(__name__)

# Pays gardés par défaut, codes ISO séparés par des virgules ; vide : tous.
COUNTRY_SETTING = "COMPANY_PAGES_COUNTRIES"
DEFAULT_COUNTRIES = "FR"

COUNTRY_NAMES = {"france": "FR", "germany": "DE", "belgium": "BE", "spain": "ES"}


def to_country_code(pCountry):
    """Retourne le code ISO d'un pays donné en code ou en nom anglais, ou None."""

    vCountry = (pCountry or "").strip()

    rCode = (
        vCountry.upper()
        if len(vCountry) == 2
        else COUNTRY_NAMES.get(vCountry.lower()) or (vCountry or None)
    )

    return rCode


def read_countries():
    """Retourne les codes des pays gardés, vides pour tous les pays."""

    vValue = os.getenv(COUNTRY_SETTING, DEFAULT_COUNTRIES)

    rCountries = {vCode.strip().upper() for vCode in vValue.split(",") if vCode.strip()}

    return rCountries


def keep_board_jobs(pJobs, pCountries, pKeyword, pLocation, pMaxItems):
    """Garde les offres du pays voulu qui correspondent aux critères, puis limite."""

    vJobs = pJobs

    # Une offre sans pays (télétravail sans lieu) reste : on ne sait pas l'exclure.
    if pCountries and not vJobs.empty:
        vJobs = vJobs[vJobs["country"].isna() | vJobs["country"].isin(pCountries)]

    vJobs = filter_by_keyword_and_location(vJobs, pKeyword, pLocation)

    rJobs = vJobs if pMaxItems is None else vJobs.head(pMaxItems)

    return rJobs


def define_board_source(pName, pLabel, pSetting, pDefaultCompanies, pFetchJobs):
    """Déclare une source de pages carrière.

    pSetting nomme la variable .env des entreprises suivies, séparées par des
    virgules ; sans entreprises par défaut, la source reste « non configurée »
    tant que cette variable est vide. pFetchJobs(entreprise) retourne le
    DataFrame Job de toutes les offres d'une entreprise.
    """

    def load_parameters(pJobConfig):
        """Construit les paramètres : entreprises, pays et critères."""

        rParameters = {
            "companies": os.getenv(pSetting) or pDefaultCompanies,
            "countries": read_countries(),
            "keyword": pJobConfig.keyword,
            "location": pJobConfig.location,
        }

        return rParameters

    def scrape_company(pParameters, pCompany, pMaxItems):
        """Récupère et filtre les offres d'une entreprise."""

        vJobs = pFetchJobs(pCompany)
        rJobs = keep_board_jobs(
            vJobs,
            pParameters["countries"],
            pParameters["keyword"],
            pParameters["location"],
            pMaxItems,
        )

        logger.info(
            "%s %s : %s offre(s) publiée(s), %s retenue(s)",
            pLabel,
            pCompany,
            len(vJobs),
            len(rJobs),
        )

        return rJobs

    def scrape(pParameters, pJobConfig):
        """Récupère les offres de chaque entreprise suivie."""

        rDataFrame = scrape_each(
            pParameters["companies"],
            lambda pCompany, pMaxItems: scrape_company(
                pParameters, pCompany, pMaxItems
            ),
            pJobConfig.max_items,
            pLabel,
        )

        return rDataFrame

    rSource = SourceDefinition(
        name=pName,
        label=pLabel,
        load_parameters=load_parameters,
        scrape=scrape,
        settings=() if pDefaultCompanies else (pSetting,),
        category="company",
    )

    return rSource


def define_feed_source(pName, pLabel, pFetchJobs, pCategory="remote"):
    """Déclare une source qui publie un flux d'offres récentes, sans recherche.

    pFetchJobs() retourne le DataFrame Job de tout le flux.
    """

    def load_parameters(pJobConfig):
        """Reprend le mot-clé et le lieu de la recherche."""

        rParameters = {"keyword": pJobConfig.keyword, "location": pJobConfig.location}

        return rParameters

    def scrape(pParameters, pJobConfig):
        """Récupère le flux, puis garde les offres qui correspondent."""

        vJobs = pFetchJobs()
        rJobs = keep_board_jobs(
            vJobs,
            set(),
            pParameters["keyword"],
            pParameters["location"],
            pJobConfig.max_items,
        )

        logger.info(
            "%s : %s offre(s) dans le flux, %s retenue(s)",
            pLabel,
            len(vJobs),
            len(rJobs),
        )

        return rJobs

    rSource = SourceDefinition(
        name=pName,
        label=pLabel,
        load_parameters=load_parameters,
        scrape=scrape,
        category=pCategory,
    )

    return rSource


def to_dataframe(pJobs):
    """Retourne les offres en DataFrame Job, colonnes dans l'ordre commun."""

    rDataFrame = pd.DataFrame(pJobs, columns=JOB_COLUMNS)

    return rDataFrame
