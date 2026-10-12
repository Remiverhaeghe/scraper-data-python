"""Transformation des données Findwork vers le format Job commun"""

import re

import pandas as pd

from job.csv_schema import JOB_COLUMNS
from utils.helpers import html_to_text, join_values

# Sans poste renseigné, la première ligne de l'annonce sert de titre si elle en a
# la forme : courte, sans « Clé : valeur » ni lien (« Remote: Yes », « https:// »).
MAX_TITLE_LENGTH = 80
NOT_A_TITLE_PATTERN = re.compile(r"^[\w\s-]{1,25}:|https?://|^[-•*]")


def guess_title(pDescription):
    """Retourne la première ligne de l'annonce si elle ressemble à un titre."""

    vLine = next(
        (vLine.strip() for vLine in (pDescription or "").splitlines() if vLine.strip()),
        "",
    )

    rTitle = (
        vLine
        if vLine
        and len(vLine) <= MAX_TITLE_LENGTH
        and not NOT_A_TITLE_PATTERN.search(vLine)
        else None
    )

    return rTitle


def parse_job(pJob):
    """Transforme une offre Findwork en dictionnaire Job.

    Le type de poste est conservé tel quel pour la détection commune
    du contrat.
    """

    vRemote = pJob.get("remote")
    vDescription = html_to_text(pJob.get("text"))

    vJob = {
        # Identification
        "title": pJob.get("role") or guess_title(vDescription),
        "company": pJob.get("company_name"),
        "company_id": None,
        "source": "findwork",
        "source_id": str(pJob.get("id")),
        "url": pJob.get("url"),
        # Localisation
        "location": pJob.get("location") or None,
        "city": None,
        "postal_code": None,
        "country": None,
        "distance_km": None,
        # Contrat
        "contract": None,
        "contract_type": pJob.get("employment_type") or None,
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
        # Dates fournies par Findwork
        "date": pJob.get("date_posted"),
        "published_at": pJob.get("date_posted"),
        "updated_at": None,
        # Dates gérées par notre application
        "scraped_at": None,
        "first_seen_at": None,
        # Contenu
        "description": vDescription,
        "missions": None,
        "requirements": None,
        "education": None,
        "skills": pJob.get("keywords") or None,
        # Informations complémentaires : site d'origine de l'offre
        "department": None,
        "experience_level": None,
        "job_type": join_values(pJob.get("source")),
    }

    rJob = vJob

    return rJob


def parse_jobs(pJobs):
    """Transforme plusieurs offres Findwork en DataFrame normalisé."""

    vJobs = [parse_job(vJob) for vJob in pJobs]

    vDataFrame = pd.DataFrame(vJobs, columns=JOB_COLUMNS)

    rDataFrame = vDataFrame

    return rDataFrame
