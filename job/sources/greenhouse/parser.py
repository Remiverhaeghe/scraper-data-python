# ============================================================================
# Transformation des données Greenhouse vers le format Job commun
# ============================================================================

import pandas as pd

from job.csv_schema import JOB_COLUMNS


def parse_job(pJob):
    """
    Transforme une offre Greenhouse en dictionnaire Job.

    :param pJob: Offre Greenhouse au format dictionnaire.
    :return: Offre normalisée.
    """

    vLocation = pJob.get("location") or {}
    vCompany = pJob.get("company") or {}

    vJob = {
        "title": pJob.get("title"),
        "company": vCompany.get("name"),
        "company_id": None,
        "source": "greenhouse",
        "source_id": str(pJob.get("id"))
        if pJob.get("id") is not None else None,
        "location": vLocation.get("name"),
        "city": None,
        "postal_code": None,
        "country": None,
        "distance_km": None,
        "contract": None,
        "contract_type": None,
        "employment_type": None,
        "salary_min": None,
        "salary_max": None,
        "salary_currency": None,
        "salary_period": None,
        "remote": None,
        "remote_days": None,
        "remote_type": None,
        "nearest_metro": None,
        "metro_distance_km": None,
        "date": pJob.get("updated_at"),
        "published_at": pJob.get("first_published"),
        "updated_at": pJob.get("updated_at"),
        "scraped_at": None,
        "url": pJob.get("absolute_url"),
        "description": pJob.get("content"),
        "missions": None,
        "requirements": None,
        "education": None,
        "skills": None,
        "department": None,
        "experience_level": None,
        "job_type": None
    }

    rJob = vJob
    return rJob


def parse_jobs(pJobs):
    """
    Transforme plusieurs offres Greenhouse en DataFrame Job.

    :param pJobs: Liste d'offres Greenhouse.
    :return: DataFrame normalisé.
    """

    vJobs = [
        parse_job(vJob)
        for vJob in pJobs
    ]

    vDataFrame = pd.DataFrame(
        vJobs,
        columns=JOB_COLUMNS
    )

    rDataFrame = vDataFrame
    return rDataFrame