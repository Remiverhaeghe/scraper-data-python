"""Transformation des données Arbeitnow vers le format Job commun"""

from datetime import UTC, datetime

import pandas as pd

from job.csv_schema import JOB_COLUMNS
from utils.helpers import html_to_text


def to_iso_date(pTimestamp):
    """Convertit un horodatage Unix en date ISO."""

    rDate = None

    if pTimestamp is not None:
        rDate = datetime.fromtimestamp(pTimestamp, UTC).isoformat()

    return rDate


def parse_job(pJob):
    """Transforme une offre Arbeitnow en dictionnaire Job.

    Les types de poste mêlent contrat, temps de travail et niveau
    d'expérience : ils sont conservés dans contract_type pour que la
    détection commune en déduise le contrat.
    """

    vRemote = pJob.get("remote")
    vCreatedAt = to_iso_date(pJob.get("created_at"))

    vJob = {
        # Identification
        "title": pJob.get("title"),
        "company": pJob.get("company_name"),
        "company_id": None,
        "source": "arbeitnow",
        "source_id": pJob.get("slug"),
        "url": pJob.get("url"),
        # Localisation
        "location": pJob.get("location") or None,
        "city": None,
        "postal_code": None,
        "country": None,
        "distance_km": None,
        # Contrat
        "contract": None,
        "contract_type": ", ".join(pJob.get("job_types") or []) or None,
        "employment_type": None,
        # Rémunération
        "salary_min": None,
        "salary_max": None,
        "salary_currency": None,
        "salary_period": None,
        "salary_label": None,
        # Télétravail
        "remote": vRemote,
        "remote_days": None,
        "remote_type": "full" if vRemote else None,
        # Transport
        "nearest_metro": None,
        "metro_distance_km": None,
        # Dates fournies par Arbeitnow
        "date": vCreatedAt,
        "published_at": vCreatedAt,
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
        "job_type": None,
    }

    rJob = vJob

    return rJob


def parse_jobs(pJobs):
    """Transforme plusieurs offres Arbeitnow en DataFrame normalisé."""

    vJobs = [parse_job(vJob) for vJob in pJobs]

    vDataFrame = pd.DataFrame(vJobs, columns=JOB_COLUMNS)

    rDataFrame = vDataFrame

    return rDataFrame
