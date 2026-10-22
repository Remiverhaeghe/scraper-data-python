"""Transformation des offres Workable vers le format Job commun"""

from job.csv_schema import build_job
from job.sources.boards import to_country_code, to_dataframe
from utils.helpers import html_to_text


def parse_job(pJob, pCompany):
    """Transforme une offre Workable en dictionnaire Job."""

    vLocation = ", ".join(
        vPart for vPart in (pJob.get("city"), pJob.get("country")) if vPart
    )

    rJob = build_job(
        title=pJob.get("title"),
        company=pCompany,
        source="workable",
        source_id=pJob.get("shortcode"),
        url=pJob.get("url"),
        location=vLocation or None,
        city=pJob.get("city") or None,
        country=to_country_code(pJob.get("country")),
        contract_type=pJob.get("employment_type") or None,
        remote=True if pJob.get("telecommuting") else None,
        date=pJob.get("published_on"),
        published_at=pJob.get("published_on"),
        description=html_to_text(pJob.get("description")),
        department=pJob.get("department") or None,
        experience_level=pJob.get("experience") or None,
        education=pJob.get("education") or None,
    )

    return rJob


def parse_account(pAccount, pAccountName):
    """Transforme les offres d'un compte en DataFrame Job."""

    vCompany = pAccount.get("name") or pAccountName

    rDataFrame = to_dataframe(
        [parse_job(vJob, vCompany) for vJob in pAccount.get("jobs") or []]
    )

    return rDataFrame
