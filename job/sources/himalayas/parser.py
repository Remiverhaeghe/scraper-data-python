"""Transformation des données Himalayas vers le format Job commun"""

import pandas as pd

from job.csv_schema import JOB_COLUMNS
from utils.helpers import html_to_text, join_values, timestamp_to_iso

SALARY_PERIODS = {"hourly": "hour", "monthly": "month", "annual": "year"}

CONTRACTS = {"Contractor": "FREELANCE", "Temporary": "CDD"}

EMPLOYMENT_TYPES = {"Full Time": "full_time", "Part Time": "part_time"}

# Au-delà, la liste des pays autorisés est résumée pour rester lisible.
MAX_LISTED_COUNTRIES = 5


def format_location(pCountries):
    """Résume la liste des pays où le candidat peut résider."""

    vCountries = pCountries or []

    rLocation = ", ".join(vCountries[:MAX_LISTED_COUNTRIES]) or None

    if len(vCountries) > MAX_LISTED_COUNTRIES:
        rLocation += f" (+{len(vCountries) - MAX_LISTED_COUNTRIES} pays)"

    return rLocation


def parse_job(pJob):
    """Transforme une offre Himalayas en dictionnaire Job."""

    vEmploymentType = pJob.get("employmentType")
    vPublishedAt = timestamp_to_iso(pJob.get("pubDate"))

    vJob = {
        # Identification
        "title": pJob.get("title"),
        "company": pJob.get("companyName"),
        "company_id": pJob.get("companySlug"),
        "source": "himalayas",
        "source_id": pJob.get("guid"),
        "url": pJob.get("applicationLink") or pJob.get("guid"),
        # Localisation : pays où le candidat doit résider
        "location": format_location(pJob.get("locationRestrictions")),
        "city": None,
        "postal_code": None,
        "country": None,
        "distance_km": None,
        # Contrat
        "contract": CONTRACTS.get(vEmploymentType),
        "contract_type": vEmploymentType,
        "employment_type": EMPLOYMENT_TYPES.get(vEmploymentType),
        # Rémunération
        "salary_min": pJob.get("minSalary"),
        "salary_max": pJob.get("maxSalary"),
        "salary_currency": pJob.get("currency"),
        "salary_period": SALARY_PERIODS.get(pJob.get("salaryPeriod")),
        "salary_label": None,
        # Télétravail : Himalayas ne publie que des postes en télétravail
        "remote": True,
        "remote_days": None,
        "remote_type": "full",
        # Transport
        "nearest_metro": None,
        "metro_distance_km": None,
        # Dates fournies par Himalayas
        "date": vPublishedAt,
        "published_at": vPublishedAt,
        "updated_at": None,
        "expires_at": timestamp_to_iso(pJob.get("expiryDate")),
        # Dates gérées par notre application
        "scraped_at": None,
        "first_seen_at": None,
        # Contenu
        "description": html_to_text(pJob.get("description")),
        "missions": None,
        "requirements": None,
        "education": None,
        "skills": pJob.get("categories") or None,
        # Informations complémentaires
        "department": None,
        "experience_level": join_values(pJob.get("seniority")),
        "job_type": join_values(pJob.get("parentCategories")),
    }

    rJob = vJob

    return rJob


def parse_jobs(pJobs):
    """Transforme plusieurs offres Himalayas en DataFrame normalisé."""

    vJobs = [parse_job(vJob) for vJob in pJobs]

    vDataFrame = pd.DataFrame(vJobs, columns=JOB_COLUMNS)

    rDataFrame = vDataFrame

    return rDataFrame
