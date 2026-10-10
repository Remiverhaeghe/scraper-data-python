"""Transformation des données Jooble vers le format Job commun"""

import pandas as pd

from job.csv_schema import JOB_COLUMNS
from utils.helpers import html_to_text


def parse_job(pJob):
    """Transforme une offre Jooble en dictionnaire Job.

    Le salaire et le type de poste sont des textes libres : ils sont
    conservés tels quels pour la détection commune du contrat et des avantages.
    """

    vJob = {
        # Identification
        "title": html_to_text(pJob.get("title")),
        "company": pJob.get("company") or None,
        "company_id": None,
        "source": "jooble",
        "source_id": str(pJob.get("id")),
        "url": pJob.get("link"),
        # Localisation
        "location": pJob.get("location") or None,
        "city": None,
        "postal_code": None,
        "country": None,
        "distance_km": None,
        # Contrat
        "contract": None,
        "contract_type": pJob.get("type") or None,
        "employment_type": None,
        # Rémunération
        "salary_min": None,
        "salary_max": None,
        "salary_currency": None,
        "salary_period": None,
        "salary_label": pJob.get("salary") or None,
        # Télétravail
        "remote": None,
        "remote_days": None,
        "remote_type": None,
        # Transport
        "nearest_metro": None,
        "metro_distance_km": None,
        # Dates fournies par Jooble
        "date": pJob.get("updated"),
        "published_at": None,
        "updated_at": pJob.get("updated"),
        # Dates gérées par notre application
        "scraped_at": None,
        "first_seen_at": None,
        # Contenu : Jooble ne fournit qu'un extrait de la description
        "description": html_to_text(pJob.get("snippet")),
        "missions": None,
        "requirements": None,
        "education": None,
        "skills": None,
        # Informations complémentaires : site d'origine de l'offre
        "department": None,
        "experience_level": None,
        "job_type": pJob.get("source") or None,
    }

    rJob = vJob

    return rJob


def parse_jobs(pJobs):
    """Transforme plusieurs offres Jooble en DataFrame normalisé."""

    vJobs = [parse_job(vJob) for vJob in pJobs]

    vDataFrame = pd.DataFrame(vJobs, columns=JOB_COLUMNS)

    rDataFrame = vDataFrame

    return rDataFrame
