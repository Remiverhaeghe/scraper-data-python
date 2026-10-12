"""Transformation des données Jooble vers le format Job commun"""

import re

import pandas as pd

from job.csv_schema import JOB_COLUMNS
from utils.helpers import html_to_text

CURRENCIES = {"€": "EUR", "$": "USD", "£": "GBP"}

# Montants au format anglais : « €1,500 », « €150k », « $15.50 »
AMOUNT_PATTERN = re.compile(r"([€$£])\s?(\d[\d,]*(?:\.\d+)?)\s?(k?)", re.IGNORECASE)

PERIOD_PATTERN = re.compile(r"per\s+(hour|month|year)", re.IGNORECASE)


def parse_salary(pLabel):
    """Extrait les bornes, la devise et la période d'un libellé de salaire Jooble."""

    vSalary = {
        "salary_min": None,
        "salary_max": None,
        "salary_currency": None,
        "salary_period": None,
    }

    vAmounts = AMOUNT_PATTERN.findall(pLabel or "")
    vPeriod = PERIOD_PATTERN.search(pLabel or "")

    if vAmounts and vPeriod:
        vValues = [
            float(vNumber.replace(",", "")) * (1000 if vThousands else 1)
            for _, vNumber, vThousands in vAmounts
        ]

        vSalary["salary_min"] = vValues[0]
        vSalary["salary_max"] = vValues[1] if len(vValues) > 1 else vValues[0]
        vSalary["salary_currency"] = CURRENCIES[vAmounts[0][0]]
        vSalary["salary_period"] = vPeriod.group(1).lower()

    rSalary = vSalary

    return rSalary


def parse_job(pJob):
    """Transforme une offre Jooble en dictionnaire Job.

    Le type de poste est un texte libre conservé tel quel ; le contrat et les
    avantages sont détectés ensuite par le traitement commun.
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
        **parse_salary(pJob.get("salary")),
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
        # Jooble ne fournit que la date de mise à jour, à défaut de publication.
        "published_at": pJob.get("updated"),
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
