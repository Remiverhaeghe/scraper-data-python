# ============================================================================
# Parsing des offres provenant de Lever
# ============================================================================

import pandas as pd

from job.csv_schema import JOB_COLUMNS


def parse_job(pJob):
    """
    Transforme une offre Lever en dictionnaire normalisé.

    :param pJob: Offre Lever.
    :return: Offre normalisée.
    """

    vCategories = pJob.get("categories") or {}

    vJob = {
        "title": pJob.get("text"),
        "company": pJob.get("company"),
        "company_id": None,
        "source": "lever",
        "source_id": pJob.get("id"),
        "url": pJob.get("hostedUrl"),

        "location": vCategories.get("location"),
        "city": None,
        "postal_code": None,
        "country": pJob.get("country"),
        "distance_km": None,

        "contract": vCategories.get("commitment"),
        "contract_type": None,
        "employment_type": vCategories.get("commitment"),

        "salary_min": None,
        "salary_max": None,
        "salary_currency": None,
        "salary_period": None,

        "remote": None,
        "remote_days": None,
        "remote_type": None,

        "nearest_metro": None,
        "metro_distance_km": None,

        "date": pJob.get("createdAt"),
        "published_at": pJob.get("createdAt"),
        "updated_at": None,

        "description": pJob.get("descriptionPlain"),
        "missions": None,
        "requirements": None,
        "education": None,
        "skills": None,

        "department": vCategories.get("department"),
        "experience_level": vCategories.get("level"),
        "job_type": vCategories.get("team")
    }

    rJob = vJob

    return rJob


def parse_jobs(pJobs):
    """
    Transforme plusieurs offres Lever en DataFrame normalisé.

    :param pJobs: Liste des offres Lever.
    :return: DataFrame des offres.
    """

    vJobs = [
        parse_job(vJob)
        for vJob in pJobs
    ]

    rData = pd.DataFrame(
        vJobs,
        columns=JOB_COLUMNS
    )

    return rData