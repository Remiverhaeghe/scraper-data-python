"""Transformation des offres Ashby vers le format Job commun"""

from job.csv_schema import build_job
from job.sources.boards import to_country_code, to_dataframe

# Type d'emploi Ashby vers un libellé lisible
EMPLOYMENT_TYPES = {
    "FullTime": "Temps plein",
    "PartTime": "Temps partiel",
    "Intern": "Stage",
    "Contract": "Contrat",
    "Temporary": "Temporaire",
}


def parse_job(pJob, pCompany):
    """Transforme une offre Ashby en dictionnaire Job."""

    vAddress = ((pJob.get("address") or {}).get("postalAddress")) or {}
    vWorkplace = (pJob.get("workplaceType") or "").lower()
    vCompensation = pJob.get("compensation") or {}

    rJob = build_job(
        title=pJob.get("title"),
        company=pCompany.replace("-", " ").title(),
        source="ashby",
        source_id=pJob.get("id"),
        url=pJob.get("jobUrl"),
        location=pJob.get("location"),
        city=vAddress.get("addressLocality"),
        country=to_country_code(vAddress.get("addressCountry")),
        contract_type=EMPLOYMENT_TYPES.get(pJob.get("employmentType")),
        salary_label=vCompensation.get("compensationTierSummary"),
        remote=True if pJob.get("isRemote") or vWorkplace == "remote" else None,
        remote_type=vWorkplace if vWorkplace in ("remote", "hybrid") else None,
        date=pJob.get("publishedAt"),
        published_at=pJob.get("publishedAt"),
        description=pJob.get("descriptionPlain"),
        department=pJob.get("department") or pJob.get("team"),
    )

    return rJob


def parse_jobs(pJobs, pCompany):
    """Transforme les offres d'une entreprise en DataFrame Job."""

    rDataFrame = to_dataframe([parse_job(vJob, pCompany) for vJob in pJobs])

    return rDataFrame
