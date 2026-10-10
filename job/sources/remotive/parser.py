"""Transformation des données Remotive vers le format Job commun"""

import pandas as pd

from job.csv_schema import JOB_COLUMNS
from utils.helpers import html_to_text

EMPLOYMENT_TYPES = ("full_time", "part_time")


def parse_job(pJob):
    """Transforme une offre Remotive en dictionnaire Job.

    Le salaire est un texte libre, le plus souvent en dollars : il est
    conservé tel quel sans être converti en net.
    """

    vJobType = pJob.get("job_type") or None

    vJob = {
        # Identification
        "title": pJob.get("title"),
        "company": pJob.get("company_name"),
        "company_id": None,
        "source": "remotive",
        "source_id": str(pJob.get("id")),
        "url": pJob.get("url"),
        # Localisation : zone géographique où le candidat doit résider
        "location": pJob.get("candidate_required_location"),
        "city": None,
        "postal_code": None,
        "country": None,
        "distance_km": None,
        # Contrat
        "contract": "FREELANCE" if vJobType == "freelance" else None,
        "contract_type": vJobType,
        "employment_type": vJobType if vJobType in EMPLOYMENT_TYPES else None,
        # Rémunération
        "salary_min": None,
        "salary_max": None,
        "salary_currency": None,
        "salary_period": None,
        "salary_label": pJob.get("salary") or None,
        # Télétravail : Remotive ne publie que des postes en télétravail
        "remote": True,
        "remote_days": None,
        "remote_type": "full",
        # Transport
        "nearest_metro": None,
        "metro_distance_km": None,
        # Dates fournies par Remotive
        "date": pJob.get("publication_date"),
        "published_at": pJob.get("publication_date"),
        "updated_at": None,
        # Dates gérées par notre application
        "scraped_at": None,
        "first_seen_at": None,
        # Contenu
        "description": html_to_text(pJob.get("description")),
        "missions": None,
        "requirements": None,
        "education": None,
        "skills": pJob.get("tags") or None,
        # Informations complémentaires
        "department": None,
        "experience_level": None,
        "job_type": pJob.get("category"),
    }

    rJob = vJob

    return rJob


def parse_jobs(pJobs):
    """Transforme plusieurs offres Remotive en DataFrame normalisé."""

    vJobs = [parse_job(vJob) for vJob in pJobs]

    vDataFrame = pd.DataFrame(vJobs, columns=JOB_COLUMNS)

    rDataFrame = vDataFrame

    return rDataFrame
