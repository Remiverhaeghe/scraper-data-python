"""Service de récupération des offres SmartRecruiters"""

import pandas as pd
import requests

from job.csv_schema import JOB_COLUMNS
from job.filter import keep_matching, matches_location
from job.sources.smartrecruiters.client import PAGE_SIZE, get_posting, get_postings
from job.sources.smartrecruiters.parser import parse_postings, read_description
from utils.logger import get_logger

logger = get_logger(__name__)

# Pages de la liste lues au plus par entreprise : 500 offres suffisent à repérer
# celles qui correspondent, sans parcourir les milliers d'offres d'un grand groupe.
MAX_PAGES = 5

# Offres gardées par entreprise sans limite donnée par la recherche
DEFAULT_MAX_DETAILS = 25

# Une description demande un appel par offre, l'un après l'autre : au-delà, une
# recherche sans mot-clé passait plusieurs minutes par grand groupe. Les offres
# suivantes sont gardées avec les champs de la liste, sans description.
MAX_DESCRIPTIONS = 50


def matches_listing(pJob, pKeyword):
    """Cherche le mot-clé dans ce que la liste fournit : titre, fonction, secteur."""

    vText = " ".join(
        str(pJob.get(vColumn) or "") for vColumn in ("title", "department", "job_type")
    ).lower()

    rMatches = pKeyword.lower() in vText

    return rMatches


def list_postings(pCompany, pCountry):
    """Lit la liste des offres d'une entreprise, page par page."""

    vPostings = []

    for vPage in range(MAX_PAGES):
        vData = get_postings(pCompany, pCountry, vPage * PAGE_SIZE)
        vContent = vData.get("content") or []
        vPostings.extend(vContent)

        if len(vContent) < PAGE_SIZE or len(vPostings) >= vData.get("totalFound", 0):
            break

    rPostings = vPostings

    return rPostings


def add_descriptions(pJobs, pCompany):
    """Complète chaque offre retenue avec sa description et son adresse publique."""

    vDescriptions = []
    vUrls = []

    for vIndex, vJob in enumerate(pJobs.to_dict("records")):
        if vIndex >= MAX_DESCRIPTIONS:
            vDescriptions.append(None)
            vUrls.append(vJob["url"])
            continue

        try:
            vDetail = get_posting(pCompany, vJob["source_id"])

        except (requests.RequestException, ValueError) as vException:
            # Une offre retirée entre la liste et le détail garde ses autres champs.
            logger.warning(
                "SmartRecruiters : détail de l'offre %s indisponible : %s",
                vJob["source_id"],
                vException,
            )
            vDetail = {}

        vDescriptions.append(read_description(vDetail))
        vUrls.append(vDetail.get("postingUrl") or vJob["url"])

    if len(pJobs) > MAX_DESCRIPTIONS:
        logger.info(
            "SmartRecruiters %s : description lue pour %s offre(s) sur %s",
            pCompany,
            MAX_DESCRIPTIONS,
            len(pJobs),
        )

    rJobs = pJobs.assign(description=vDescriptions, url=vUrls)

    return rJobs


def scrape_jobs(pCompany, pCountry, pKeyword=None, pLocation=None, pMaxItems=None):
    """Récupère, filtre et complète les offres d'une entreprise SmartRecruiters.

    Le filtre par mot-clé et par lieu se fait sur la liste, avant de lire le
    détail : seules les offres retenues coûtent un appel supplémentaire.
    """

    logger.info("Début du scraping SmartRecruiters : %s", pCompany)

    vPostings = list_postings(pCompany, pCountry)
    vJobs = parse_postings(vPostings, pCompany)

    if pKeyword:
        vJobs = keep_matching(vJobs, lambda pJob: matches_listing(pJob, pKeyword))

    if pLocation:
        vJobs = keep_matching(vJobs, lambda pJob: matches_location(pJob, pLocation))

    vJobs = vJobs.head(pMaxItems if pMaxItems is not None else DEFAULT_MAX_DETAILS)

    rJobs = (
        add_descriptions(vJobs, pCompany)
        if not vJobs.empty
        else pd.DataFrame(columns=JOB_COLUMNS)
    )

    logger.info(
        "SmartRecruiters %s : %s offre(s) lue(s), %s retenue(s)",
        pCompany,
        len(vPostings),
        len(rJobs),
    )

    return rJobs
