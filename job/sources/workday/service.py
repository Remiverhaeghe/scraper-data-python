"""Service de récupération des offres des sites carrière Workday"""

from datetime import datetime
from urllib.parse import urlparse

import pandas as pd
import requests

from job.csv_schema import JOB_COLUMNS
from job.filter import keep_matching, matches_location
from job.sources.workday.client import (
    PAGE_SIZE,
    WorkdaySite,
    get_job,
    parse_site,
    search_jobs,
)
from job.sources.workday.parser import parse_postings, read_detail
from utils.logger import get_logger

logger = get_logger(__name__)

# Pays gardé, tel que Workday le nomme dans ses filtres
COUNTRY = "France"

# Pages lues au plus par entreprise : 200 offres après le filtre du pays et du
# mot-clé, faits par Workday.
MAX_PAGES = 10

# Offres gardées par entreprise sans limite donnée par la recherche
DEFAULT_MAX_ITEMS = 25

# Une description coûte un appel par offre ; les suivantes sont lues à
# l'ouverture de la fiche (job/offer_details.py).
MAX_DESCRIPTIONS = 50


def find_country_facet(pFacets, pCountry):
    """Retourne (paramètre, identifiant) du filtre de pays, ou None sans ce filtre.

    Les filtres de lieu sont parfois regroupés : la recherche descend dans les
    groupes.
    """

    for vFacet in pFacets:
        vParameter = str(vFacet.get("facetParameter") or "")

        for vValue in vFacet.get("values") or []:
            if vValue.get("facetParameter"):
                vFound = find_country_facet([vValue], pCountry)

                if vFound:
                    return vFound

            elif (
                "country" in vParameter.lower() and vValue.get("descriptor") == pCountry
            ):
                return (vParameter, vValue["id"])

    return None


def list_postings(pSite, pKeyword):
    """Lit les offres du pays d'une entreprise, page par page.

    Sans filtre de pays, cas d'une entreprise seulement française, toutes les
    offres sont lues.
    """

    vFirstPage = search_jobs(pSite, pKeyword, 0)
    vFacet = find_country_facet(vFirstPage.get("facets") or [], COUNTRY)

    if vFacet is None:
        logger.info(
            "Workday %s : pas de filtre par pays, toutes les offres", pSite.name
        )
        vFacets = None
        vData = vFirstPage
    else:
        vFacets = {vFacet[0]: [vFacet[1]]}
        vData = search_jobs(pSite, pKeyword, 0, vFacets)

    # Le total n'est donné qu'avec la première page.
    vTotal = vData.get("total") or 0
    vPostings = list(vData.get("jobPostings") or [])

    for vPage in range(1, MAX_PAGES):
        if len(vPostings) >= vTotal or len(vPostings) < vPage * PAGE_SIZE:
            break

        vPostings.extend(
            search_jobs(pSite, pKeyword, vPage * PAGE_SIZE, vFacets).get("jobPostings")
            or []
        )

    rPostings = vPostings

    return rPostings


def read_job_path(pSite, pUrl):
    """Retourne le chemin d'une offre dans l'API, lu dans son adresse publique."""

    rPath = urlparse(str(pUrl)).path.removeprefix(f"/{pSite.site}")

    return rPath


def add_descriptions(pJobs, pSite, pKnown=None):
    """Complète les premières offres avec leur description et leur temps de travail.

    Une offre déjà décrite en base (pKnown) est reprise sans appel réseau : le
    plafond ne compte que les offres réellement lues.
    """

    vKnown = pKnown or {}
    vDescriptions = []
    vTypes = []
    vRead = 0

    for vJob in pJobs.to_dict("records"):
        vDetail = vKnown.get(str(vJob["source_id"])) or {}

        if not vDetail and vRead < MAX_DESCRIPTIONS:
            vRead += 1

            try:
                vDetail = read_detail(get_job(pSite, read_job_path(pSite, vJob["url"])))

            except (requests.RequestException, ValueError) as vException:
                logger.warning(
                    "Workday %s : détail de l'offre %s indisponible : %s",
                    pSite.name,
                    vJob["source_id"],
                    vException,
                )

        vDescriptions.append(vDetail.get("description"))
        vTypes.append(vDetail.get("employment_type"))

    logger.info(
        "Workday %s : %s description(s) lue(s), %s reprise(s) de la base, sur %s "
        "offre(s)",
        pSite.name,
        vRead,
        sum(1 for vJob in pJobs["source_id"] if str(vJob) in vKnown),
        len(pJobs),
    )

    rJobs = pJobs.assign(description=vDescriptions, employment_type=vTypes)

    return rJobs


def scrape_jobs(
    pSiteText, pKeyword=None, pLocation=None, pMaxItems=None, pNow=None, pKnown=None
):
    """Récupère, filtre et complète les offres d'un site carrière Workday."""

    vSite = parse_site(pSiteText)

    logger.info("Début du scraping Workday : %s", vSite.name)

    vPostings = list_postings(vSite, pKeyword)
    vJobs = parse_postings(vPostings, vSite, pNow or datetime.now())

    if pLocation:
        vJobs = keep_matching(vJobs, lambda pJob: matches_location(pJob, pLocation))

    vJobs = vJobs.head(pMaxItems if pMaxItems is not None else DEFAULT_MAX_ITEMS)

    rJobs = (
        add_descriptions(vJobs, vSite, pKnown)
        if not vJobs.empty
        else pd.DataFrame(columns=JOB_COLUMNS)
    )

    logger.info(
        "Workday %s : %s offre(s) lue(s), %s retenue(s)",
        vSite.name,
        len(vPostings),
        len(rJobs),
    )

    return rJobs


def read_site_from_url(pOffer):
    """Retrouve le site d'une offre enregistrée, d'après son adresse, ou None.

    Adresse : https://<hôte>.myworkdayjobs.com/<site>/job/... ; le tenant est
    au début de l'identifiant (job/sources/workday/parser.py).
    """

    vUrl = urlparse(str(pOffer.get("url") or ""))
    vHost = vUrl.netloc.removesuffix(".myworkdayjobs.com")
    vSite = vUrl.path.strip("/").split("/", 1)[0]
    vTenant = str(pOffer.get("source_id") or "").split(":", 1)[0]

    rSite = (
        WorkdaySite(pOffer.get("company") or vTenant, vHost, vTenant, vSite)
        if vHost != vUrl.netloc and vSite and vTenant
        else None
    )

    return rSite


def fetch_description(pOffer):
    """Lit la description d'une offre enregistrée sans elle ; retourne (texte, adresse).

    Retourne None si l'adresse ne désigne pas un site Workday.
    """

    vSite = read_site_from_url(pOffer)

    if vSite is None:
        return None

    vDetail = read_detail(get_job(vSite, read_job_path(vSite, pOffer["url"])))

    rDescription = (vDetail["description"], pOffer["url"])

    return rDescription
