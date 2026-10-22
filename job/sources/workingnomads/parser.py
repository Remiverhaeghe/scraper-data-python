"""Transformation des offres Working Nomads vers le format Job commun"""

import re

from job.csv_schema import build_job
from job.sources.boards import to_dataframe
from utils.helpers import html_to_text

# Identifiant numérique de l'offre dans son adresse : /job/go/1960693/
JOB_ID_PATTERN = re.compile(r"/(\d+)/?$")


def parse_job(pJob):
    """Transforme une offre Working Nomads en dictionnaire Job."""

    vUrl = pJob.get("url") or ""
    vMatch = JOB_ID_PATTERN.search(vUrl)

    rJob = build_job(
        title=pJob.get("title"),
        company=pJob.get("company_name"),
        source="workingnomads",
        # L'API ne donne pas d'identifiant : il est lu dans l'adresse de l'offre.
        source_id=vMatch.group(1) if vMatch else vUrl or None,
        url=vUrl or None,
        location=pJob.get("location") or None,
        remote=True,
        remote_type="full",
        date=pJob.get("pub_date"),
        published_at=pJob.get("pub_date"),
        description=html_to_text(pJob.get("description")),
        skills=(pJob.get("tags") or "").replace(",", ", ") or None,
        job_type=pJob.get("category_name"),
    )

    return rJob


def parse_jobs(pJobs):
    """Transforme les offres en DataFrame Job."""

    rDataFrame = to_dataframe([parse_job(vJob) for vJob in pJobs])

    return rDataFrame
