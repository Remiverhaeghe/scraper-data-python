"""Transformation des données Greenhouse vers le format Job commun"""

import pandas as pd

from job.csv_schema import JOB_COLUMNS


def parse_job(pJob):
    """Transforme une offre Greenhouse en dictionnaire Job.

    Les données propres à Greenhouse sont converties
    vers le modèle commun utilisé par les différentes sources.
    """

    vLocation = pJob.get("location") or {}
    vCompany = pJob.get("company") or {}

    vJob = {
        # Identification
        "title": pJob.get("title"),
        "company": vCompany.get("name"),
        "company_id": None,
        "source": "greenhouse",
        "source_id": (str(pJob.get("id")) if pJob.get("id") is not None else None),
        "url": pJob.get("absolute_url"),
        # Localisation
        "location": vLocation.get("name"),
        "city": None,
        "postal_code": None,
        "country": None,
        "distance_km": None,
        # Contrat
        "contract": None,
        "contract_type": None,
        "employment_type": None,
        # Rémunération
        "salary_min": None,
        "salary_max": None,
        "salary_currency": None,
        "salary_period": None,
        # Télétravail
        "remote": None,
        "remote_days": None,
        "remote_type": None,
        # Transport
        "nearest_metro": None,
        "metro_distance_km": None,
        # Dates fournies par Greenhouse
        "date": pJob.get("updated_at"),
        "published_at": pJob.get("first_published"),
        "updated_at": pJob.get("updated_at"),
        # Dates gérées par notre application
        "scraped_at": None,
        "first_seen_at": None,
        # Contenu
        "description": pJob.get("content"),
        "missions": None,
        "requirements": None,
        "education": None,
        "skills": None,
        # Informations complémentaires
        "department": None,
        "experience_level": None,
        "job_type": None,
    }

    rJob = vJob

    return rJob


def parse_jobs(pJobs):
    """Transforme plusieurs offres Greenhouse en DataFrame Job."""

    vJobs = [parse_job(vJob) for vJob in pJobs]

    vDataFrame = pd.DataFrame(vJobs, columns=JOB_COLUMNS)

    rDataFrame = vDataFrame

    return rDataFrame
