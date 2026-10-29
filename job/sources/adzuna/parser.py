"""Transformation des données Adzuna vers le format Job commun"""

import re

import pandas as pd

from job.csv_schema import JOB_COLUMNS
from utils.helpers import decode_unicode_escapes, html_to_text

# « contract » couvre aussi bien un CDD qu'une mission freelance : il est
# laissé à la détection commune.
CONTRACTS = {"permanent": "CDI"}

# Adzuna ne nomme pas l'entreprise des annonces d'agences d'intérim, mais le
# texte le fait : « Votre agence d'intérim PROMAN recrute », « PROMAN Niort
# recherche ». Le nom de l'agence est écrit en capitales.
AGENCY_PATTERNS = (
    re.compile(
        r"\bagence\s+(?:d['’]int[ée]rim\s+|d['’]emploi\s+)?"
        r"(?P<name>[A-Z]{3,}[A-Z0-9&-]*)\b"
    ),
    re.compile(
        r"^\W*(?P<name>[A-Z]{3,}[A-Z0-9&-]*)\b(?=[^.!?]{0,100}\b(?:recrute|recherche))"
    ),
)

# Mots en capitales qui ouvrent une annonce sans être un nom d'agence
NOT_AGENCIES = {"CDI", "CDD", "URGENT", "IMPORTANT", "POSTE", "MISSION", "OFFRE"}

# Adzuna présente ses salaires comme annuels, mais l'employeur saisit parfois un
# taux horaire (12 €) ou un salaire mensuel (2 100 €) : la période se lit au
# montant, sinon ces postes seraient écartés et fausseraient la médiane.
MAX_HOURLY_SALARY = 200
MAX_MONTHLY_SALARY = 10000


def read_salary_period(pAmount):
    """Retourne la période d'un salaire Adzuna d'après son montant : heure, mois ou an."""

    if pAmount < MAX_HOURLY_SALARY:
        rPeriod = "hour"
    elif pAmount < MAX_MONTHLY_SALARY:
        rPeriod = "month"
    else:
        rPeriod = "year"

    return rPeriod


def find_agency(pText):
    """Retourne l'agence qui publie l'annonce, nommée dans son texte, ou None."""

    rAgency = None

    for vPattern in AGENCY_PATTERNS:
        vMatch = vPattern.search(pText or "")

        if vMatch and vMatch.group("name") not in NOT_AGENCIES:
            rAgency = vMatch.group("name")
            break

    return rAgency


def read_text(pValue):
    """Décode les échappements Unicode, puis les balises et entités HTML (&eacute;)."""

    rText = html_to_text(decode_unicode_escapes(pValue))

    return rText


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
        "title": read_text(pJob.get("title")),
        "company": vCompany.get("display_name")
        or find_agency(read_text(pJob.get("description"))),
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
        "salary_min": vSalaryMin,
        "salary_max": vSalaryMax,
        "salary_currency": "EUR" if vHasSalary else None,
        "salary_period": (
            read_salary_period(max(vSalaryMin or 0, vSalaryMax or 0))
            if vHasSalary
            else None
        ),
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
        # Adzuna renvoie parfois le texte avec ses accents encore échappés
        "description": read_text(pJob.get("description")),
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
