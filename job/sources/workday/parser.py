"""Transformation des offres Workday vers le format Job commun"""

import re
from datetime import timedelta

import pandas as pd

from job.csv_schema import JOB_COLUMNS, build_job
from utils.helpers import html_to_text

# Ancienneté donnée en toutes lettres : « Posted Today », « Posted 3 Days Ago »,
# « Posted 30+ Days Ago »
POSTED_DAYS_PATTERN = re.compile(r"(\d+)\+? Days? Ago", re.IGNORECASE)


def read_posted_date(pPostedOn, pNow):
    """Retourne la date de publication déduite de son ancienneté, ou None."""

    vText = str(pPostedOn or "").lower()
    vMatch = POSTED_DAYS_PATTERN.search(vText)

    if vMatch:
        vDays = int(vMatch.group(1))
    elif "today" in vText:
        vDays = 0
    elif "yesterday" in vText:
        vDays = 1
    else:
        return None

    rDate = (pNow - timedelta(days=vDays)).date().isoformat()

    return rDate


def build_source_id(pSite, pExternalPath):
    """Retourne l'identifiant d'une offre : tenant et référence, uniques entre sites."""

    # Chemin : /job/Lille-Hauts-de-France/Adjoint-de-laboratoire_R9955
    vReference = str(pExternalPath).rstrip("/").rsplit("_", 1)[-1]

    rSourceId = f"{pSite.tenant}:{vReference}"

    return rSourceId


def parse_posting(pPosting, pSite, pNow):
    """Transforme une offre de la liste en dictionnaire Job, sans description."""

    vPath = pPosting.get("externalPath") or ""
    vPublished = read_posted_date(pPosting.get("postedOn"), pNow)

    rJob = build_job(
        title=pPosting.get("title"),
        company=pSite.name,
        source="workday",
        source_id=build_source_id(pSite, vPath) if vPath else None,
        url=f"{pSite.page_url}{vPath}",
        location=pPosting.get("locationsText"),
        date=vPublished,
        published_at=vPublished,
    )

    return rJob


def read_detail(pDetail):
    """Retourne la description et le temps de travail lus dans le détail."""

    vInfo = pDetail.get("jobPostingInfo") or {}

    rDetail = {
        "description": html_to_text(vInfo.get("jobDescription")),
        "employment_type": vInfo.get("timeType"),
    }

    return rDetail


def parse_postings(pPostings, pSite, pNow):
    """Transforme une liste d'offres en DataFrame Job."""

    rDataFrame = pd.DataFrame(
        [parse_posting(vPosting, pSite, pNow) for vPosting in pPostings],
        columns=JOB_COLUMNS,
    )

    return rDataFrame
