"""Transformation des offres Hacker News vers le format Job commun"""

import re

import pandas as pd

from job.csv_schema import JOB_COLUMNS
from utils.helpers import html_to_text

ITEM_URL = "https://news.ycombinator.com/item?id={id}"

# Séparateurs usuels de la ligne d'en-tête : « Entreprise | Poste | Lieu »
HEADER_SEPARATOR = re.compile(r"\s+[|–—]\s+")

REMOTE_PATTERN = re.compile(r"\bremote\b", re.IGNORECASE)

# Lien vers le site de l'entreprise, parfois entre parenthèses, après son nom
COMPANY_URL_PATTERN = re.compile(r"\(?\s*https?://[^\s)]+\s*\)?")


def split_header(pText):
    """Sépare la première ligne d'une offre, du reste de son contenu."""

    vParts = (pText or "").split("<p>", 1)

    vHeader = html_to_text(vParts[0]) or ""
    vBody = vParts[1] if len(vParts) > 1 else ""

    rHeader = (vHeader, vBody)

    return rHeader


def parse_job(pComment):
    """Transforme un commentaire du fil « Who is hiring? » en dictionnaire Job.

    Les offres sont rédigées en texte libre : seule la convention de la
    première ligne permet d'en extraire l'entreprise et le poste.
    """

    vHeader, vBody = split_header(pComment.get("text"))
    vSegments = HEADER_SEPARATOR.split(vHeader)

    vCompany = COMPANY_URL_PATTERN.sub("", vSegments[0]).strip() or None
    vDetails = " | ".join(vSegments[1:]) or vHeader

    vJob = {
        # Identification
        "title": vDetails[:200] or None,
        "company": vCompany,
        "company_id": None,
        "source": "hackernews",
        "source_id": str(pComment.get("id")),
        "url": ITEM_URL.format(id=pComment.get("id")),
        # Localisation : mentionnée librement dans l'en-tête
        "location": vHeader[:200] or None,
        "city": None,
        "postal_code": None,
        "country": None,
        "distance_km": None,
        # Contrat
        "contract": None,
        "contract_type": None,
        "employment_type": None,
        # Rémunération
        "salary_min": None,
        "salary_max": None,
        "salary_currency": None,
        "salary_period": None,
        "salary_label": None,
        # Télétravail
        "remote": True if REMOTE_PATTERN.search(vHeader) else None,
        "remote_days": None,
        "remote_type": None,
        # Transport
        "nearest_metro": None,
        "metro_distance_km": None,
        # Dates fournies par Hacker News
        "date": pComment.get("created_at"),
        "published_at": pComment.get("created_at"),
        "updated_at": None,
        # Dates gérées par notre application
        "scraped_at": None,
        "first_seen_at": None,
        # Contenu
        "description": html_to_text(vBody),
        "missions": None,
        "requirements": None,
        "education": None,
        "skills": None,
        # Informations complémentaires
        "department": None,
        "experience_level": None,
        "job_type": None,
    }

    rJob = vJob

    return rJob


def parse_jobs(pComments):
    """Transforme les offres d'un fil en DataFrame normalisé.

    Les commentaires supprimés n'ont pas de texte et sont ignorés.
    """

    vJobs = [parse_job(vComment) for vComment in pComments if vComment.get("text")]

    vDataFrame = pd.DataFrame(vJobs, columns=JOB_COLUMNS)

    rDataFrame = vDataFrame

    return rDataFrame
