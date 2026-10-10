"""Transformation des données France Travail vers le format Job commun"""

import re

import pandas as pd

from job.csv_schema import JOB_COLUMNS

OFFER_URL = "https://candidat.francetravail.fr/offres/recherche/detail/"

SALARY_PERIODS = {"Horaire": "hour", "Mensuel": "month", "Annuel": "year"}

# Exemple : "Mensuel de 2000.00 Euros à 2500.00 Euros sur 12 mois"
SALARY_PATTERN = re.compile(
    r"^(Horaire|Mensuel|Annuel) de ([\d.]+) Euros(?: à ([\d.]+) Euros)?"
)


def parse_salary(pLabel):
    """Extrait le minimum, le maximum et la période d'un libellé de salaire."""

    rSalary = (None, None, None)

    vMatch = SALARY_PATTERN.match(pLabel or "")

    if vMatch:
        vPeriod, vMin, vMax = vMatch.groups()

        rSalary = (
            float(vMin),
            float(vMax) if vMax else None,
            SALARY_PERIODS[vPeriod],
        )

    return rSalary


def parse_job(pJob):
    """Transforme une offre France Travail en dictionnaire Job.

    Les données propres à France Travail sont converties
    vers le modèle commun utilisé par les différentes sources.
    """

    vEntreprise = pJob.get("entreprise") or {}
    vLieu = pJob.get("lieuTravail") or {}
    vSalaire = pJob.get("salaire") or {}

    vJob = {
        # Identification
        "title": pJob.get("intitule"),
        "company": vEntreprise.get("nom"),
        "company_id": None,
        "source": "france_travail",
        "source_id": pJob.get("id"),
        "url": (pJob.get("origineOffre") or {}).get("urlOrigine")
        or OFFER_URL + str(pJob.get("id")),
        # Localisation
        "location": vLieu.get("libelle"),
        "city": vLieu.get("commune"),
        "postal_code": vLieu.get("codePostal"),
        "country": "France",
        "distance_km": None,
        # Contrat
        "contract": pJob.get("typeContratLibelle"),
        "contract_type": pJob.get("typeContrat"),
        "employment_type": None,
        # Rémunération
        "salary_min": None,
        "salary_max": None,
        "salary_currency": "EUR",
        "salary_period": None,
        # Télétravail
        "remote": None,
        "remote_days": None,
        "remote_type": None,
        # Transport
        "nearest_metro": None,
        "metro_distance_km": None,
        # Dates fournies par France Travail
        "date": pJob.get("dateCreation"),
        "published_at": pJob.get("dateCreation"),
        "updated_at": pJob.get("dateActualisation"),
        # Dates gérées par notre application
        "scraped_at": None,
        "first_seen_at": None,
        # Contenu
        "description": pJob.get("description"),
        "missions": None,
        "requirements": None,
        "education": pJob.get("formations"),
        "skills": pJob.get("competences"),
        # Informations complémentaires
        "department": None,
        "experience_level": pJob.get("experienceLibelle"),
        "job_type": None,
    }

    vSalaryMin, vSalaryMax, vSalaryPeriod = parse_salary(vSalaire.get("libelle"))

    vJob["salary_min"] = vSalaryMin
    vJob["salary_max"] = vSalaryMax
    vJob["salary_period"] = vSalaryPeriod

    rJob = vJob

    return rJob


def parse_jobs(pJobs):
    """Transforme plusieurs offres France Travail en DataFrame Job."""

    vJobs = [parse_job(vJob) for vJob in pJobs]

    vDataFrame = pd.DataFrame(vJobs, columns=JOB_COLUMNS)

    rDataFrame = vDataFrame

    return rDataFrame
