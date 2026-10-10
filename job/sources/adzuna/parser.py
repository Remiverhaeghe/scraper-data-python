"""Transformation des données Adzuna vers le format Job commun"""

import pandas as pd

from job.csv_schema import JOB_COLUMNS

CONTRACTS = {"permanent": "CDI", "contract": "CDD / mission"}


def parse_job(pJob):
    """Transforme une offre Adzuna en dictionnaire Job.

    Les salaires estimés par Adzuna sont ignorés : seuls les salaires
    annoncés par l'employeur sont conservés.
    """

    vCompany = pJob.get("company") or {}
    vLocation = pJob.get("location") or {}
    vArea = vLocation.get("area") or []
    vCategory = pJob.get("category") or {}

    vHasRealSalary = str(pJob.get("salary_is_predicted")) != "1"
    vSalaryMin = pJob.get("salary_min") if vHasRealSalary else None
    vSalaryMax = pJob.get("salary_max") if vHasRealSalary else None
    vHasSalary = vSalaryMin is not None or vSalaryMax is not None

    vJob = {
        # Identification
        "title": pJob.get("title"),
        "company": vCompany.get("display_name"),
        "company_id": None,
        "source": "adzuna",
        "source_id": pJob.get("id"),
        "url": pJob.get("redirect_url"),
        # Localisation : area va du pays vers la commune
        "location": vLocation.get("display_name"),
        "city": vArea[3] if len(vArea) > 3 else None,
        "postal_code": None,
        "country": vArea[0] if vArea else None,
        "distance_km": None,
        # Contrat
        "contract": CONTRACTS.get(pJob.get("contract_type")),
        "contract_type": pJob.get("contract_type"),
        "employment_type": pJob.get("contract_time"),
        # Rémunération, annualisée par Adzuna
        "salary_min": vSalaryMin,
        "salary_max": vSalaryMax,
        "salary_currency": "EUR" if vHasSalary else None,
        "salary_period": "year" if vHasSalary else None,
        "salary_label": None,
        # Télétravail
        "remote": None,
        "remote_days": None,
        "remote_type": None,
        # Transport
        "nearest_metro": None,
        "metro_distance_km": None,
        # Dates fournies par Adzuna
        "date": pJob.get("created"),
        "published_at": pJob.get("created"),
        "updated_at": None,
        # Dates gérées par notre application
        "scraped_at": None,
        "first_seen_at": None,
        # Contenu : Adzuna ne fournit qu'un extrait de la description
        "description": pJob.get("description"),
        "missions": None,
        "requirements": None,
        "education": None,
        "skills": None,
        # Informations complémentaires
        "department": None,
        "experience_level": None,
        "job_type": vCategory.get("label"),
    }

    rJob = vJob

    return rJob


def parse_jobs(pJobs):
    """Transforme plusieurs offres Adzuna en DataFrame normalisé."""

    vJobs = [parse_job(vJob) for vJob in pJobs]

    vDataFrame = pd.DataFrame(vJobs, columns=JOB_COLUMNS)

    rDataFrame = vDataFrame

    return rDataFrame
