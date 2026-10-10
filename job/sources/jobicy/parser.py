"""Transformation des données Jobicy vers le format Job commun"""

import pandas as pd

from job.csv_schema import JOB_COLUMNS
from utils.helpers import html_to_text, join_values

SALARY_PERIODS = {"hourly": "hour", "monthly": "month", "yearly": "year"}

EMPLOYMENT_TYPES = {"Full-Time": "full_time", "Part-Time": "part_time"}


def parse_job(pJob):
    """Transforme une offre Jobicy en dictionnaire Job.

    Le type de poste « Contract » peut désigner un CDD comme une mission :
    il est laissé à la détection commune.
    """

    vJobType = join_values(pJob.get("jobType"))

    vJob = {
        # Identification
        "title": pJob.get("jobTitle"),
        "company": pJob.get("companyName"),
        "company_id": None,
        "source": "jobicy",
        "source_id": str(pJob.get("id")),
        "url": pJob.get("url"),
        # Localisation : zone géographique ouverte aux candidats
        "location": " ".join((pJob.get("jobGeo") or "").split()) or None,
        "city": None,
        "postal_code": None,
        "country": None,
        "distance_km": None,
        # Contrat
        "contract": None,
        "contract_type": vJobType,
        "employment_type": EMPLOYMENT_TYPES.get(vJobType),
        # Rémunération
        "salary_min": pJob.get("salaryMin"),
        "salary_max": pJob.get("salaryMax"),
        "salary_currency": pJob.get("salaryCurrency"),
        "salary_period": SALARY_PERIODS.get(pJob.get("salaryPeriod")),
        "salary_label": None,
        # Télétravail : Jobicy ne publie que des postes en télétravail
        "remote": True,
        "remote_days": None,
        "remote_type": "full",
        # Transport
        "nearest_metro": None,
        "metro_distance_km": None,
        # Dates fournies par Jobicy
        "date": pJob.get("pubDate"),
        "published_at": pJob.get("pubDate"),
        "updated_at": None,
        # Dates gérées par notre application
        "scraped_at": None,
        "first_seen_at": None,
        # Contenu
        "description": html_to_text(pJob.get("jobDescription")),
        "missions": None,
        "requirements": None,
        "education": None,
        "skills": None,
        # Informations complémentaires
        "department": None,
        "experience_level": pJob.get("jobLevel"),
        "job_type": join_values(pJob.get("jobIndustry")),
    }

    rJob = vJob

    return rJob


def parse_jobs(pJobs):
    """Transforme plusieurs offres Jobicy en DataFrame normalisé."""

    vJobs = [parse_job(vJob) for vJob in pJobs]

    vDataFrame = pd.DataFrame(vJobs, columns=JOB_COLUMNS)

    rDataFrame = vDataFrame

    return rDataFrame
