# ============================================================================
# Transformation des données France Travail vers le format Job commun
# ============================================================================

import pandas as pd

from job.csv_schema import JOB_COLUMNS


def parse_job(pJob):
    """
    Transforme une offre France Travail en dictionnaire Job.

    :param pJob: Offre France Travail au format dictionnaire.
    :return: Offre normalisée.
    """

    vEntreprise = pJob.get("entreprise") or {}
    vLieu = pJob.get("lieuTravail") or {}
    vSalaire = pJob.get("salaire") or {}

    vJob = {
        "title": pJob.get("intitule"),
        "company": vEntreprise.get("nom"),
        "company_id": None,
        "source": "france_travail",
        "source_id": pJob.get("id"),
        "location": vLieu.get("libelle"),
        "city": vLieu.get("commune"),
        "postal_code": vLieu.get("codePostal"),
        "country": "France",
        "distance_km": None,
        "contract": pJob.get("typeContratLibelle"),
        "contract_type": pJob.get("typeContrat"),
        "employment_type": None,
        "salary_min": None,
        "salary_max": None,
        "salary_currency": "EUR",
        "salary_period": None,
        "remote": None,
        "remote_days": None,
        "remote_type": None,
        "nearest_metro": None,
        "metro_distance_km": None,
        "date": pJob.get("dateCreation"),
        "published_at": pJob.get("dateCreation"),
        "updated_at": pJob.get("dateActualisation"),
        "scraped_at": None,
        "url": pJob.get("origineOffre", {}).get("urlOrigine"),
        "description": pJob.get("description"),
        "missions": None,
        "requirements": None,
        "education": pJob.get("formations"),
        "skills": pJob.get("competences"),
        "department": None,
        "experience_level": pJob.get("experienceLibelle"),
        "job_type": None
    }

    if vSalaire:
        vJob["salary_min"] = vSalaire.get("min")
        vJob["salary_max"] = vSalaire.get("max")
        vJob["salary_period"] = vSalaire.get("libelle")

    rJob = vJob
    return rJob


def parse_jobs(pJobs):
    """
    Transforme plusieurs offres France Travail en DataFrame Job.

    :param pJobs: Liste d'offres France Travail.
    :return: DataFrame normalisé.
    """

    vJobs = [
        parse_job(vJob)
        for vJob in pJobs
    ]

    vDataFrame = pd.DataFrame(
        vJobs,
        columns=JOB_COLUMNS
    )

    rDataFrame = vDataFrame
    return rDataFrame