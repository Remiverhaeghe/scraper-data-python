"""Transformation des données Lever vers le format Job commun"""

import pandas as pd

from job.csv_schema import JOB_COLUMNS

SALARY_PERIODS = {
    "per-hour-wage": "hour",
    "per-month-salary": "month",
    "per-year-salary": "year",
}


def parse_job(pJob):
    """Transforme une offre Lever en dictionnaire Job.

    Les données propres à Lever sont converties
    vers le modèle commun utilisé par les différentes sources.
    """

    vCategories = pJob.get("categories") or {}
    vSalaryRange = pJob.get("salaryRange") or {}

    vJob = {
        # Identification
        "title": pJob.get("text"),
        "company": pJob.get("company"),
        "company_id": None,
        "source": "lever",
        "source_id": pJob.get("id"),
        "url": pJob.get("hostedUrl"),
        # Localisation
        "location": vCategories.get("location"),
        "city": None,
        "postal_code": None,
        "country": pJob.get("country"),
        "distance_km": None,
        # Contrat
        "contract": None,
        "contract_type": vCategories.get("commitment"),
        "employment_type": vCategories.get("commitment"),
        # Rémunération
        "salary_min": vSalaryRange.get("min"),
        "salary_max": vSalaryRange.get("max"),
        "salary_currency": vSalaryRange.get("currency"),
        "salary_period": SALARY_PERIODS.get(vSalaryRange.get("interval")),
        # Télétravail
        "remote": None,
        "remote_days": None,
        "remote_type": None,
        # Transport
        "nearest_metro": None,
        "metro_distance_km": None,
        # Dates fournies par Lever
        "date": pJob.get("createdAt"),
        "published_at": pJob.get("createdAt"),
        "updated_at": None,
        # Dates gérées par notre application
        "scraped_at": None,
        "first_seen_at": None,
        # Contenu
        "description": pJob.get("descriptionPlain"),
        "missions": None,
        "requirements": None,
        "education": None,
        "skills": None,
        # Informations complémentaires
        "department": vCategories.get("department"),
        "experience_level": vCategories.get("level"),
        "job_type": vCategories.get("team"),
    }

    rJob = vJob

    return rJob


def parse_jobs(pJobs):
    """Transforme plusieurs offres Lever en DataFrame normalisé."""

    vJobs = [parse_job(vJob) for vJob in pJobs]

    vDataFrame = pd.DataFrame(vJobs, columns=JOB_COLUMNS)

    rDataFrame = vDataFrame

    return rDataFrame
