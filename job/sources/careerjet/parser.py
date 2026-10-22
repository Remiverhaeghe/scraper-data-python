"""Transformation des offres Careerjet vers le format Job commun"""

import hashlib
from email.utils import parsedate_to_datetime

from job.csv_schema import build_job
from job.sources.boards import to_dataframe
from utils.helpers import html_to_text

# Période du salaire Careerjet vers la période commune
SALARY_PERIODS = {"Y": "year", "M": "month", "H": "hour"}


def build_source_id(pJob):
    """Retourne un identifiant stable : l'API n'en donne pas et ses liens changent."""

    vKey = "|".join(
        str(pJob.get(vField) or "")
        for vField in ("title", "company", "locations", "date")
    )

    rSourceId = hashlib.sha256(vKey.encode("utf-8")).hexdigest()[:24]

    return rSourceId


def to_iso_date(pDate):
    """Convertit une date Careerjet (« Wed, 15 Nov 2025 19:13:43 GMT ») au format ISO."""

    try:
        rDate = parsedate_to_datetime(pDate).isoformat() if pDate else None
    except (TypeError, ValueError):
        rDate = None

    return rDate


def parse_job(pJob):
    """Transforme une offre Careerjet en dictionnaire Job."""

    vPeriod = SALARY_PERIODS.get(pJob.get("salary_type"))

    rJob = build_job(
        title=pJob.get("title"),
        company=pJob.get("company") or None,
        source="careerjet",
        source_id=build_source_id(pJob),
        # Lien de suivi fourni par Careerjet, à garder tel quel
        url=pJob.get("url"),
        location=pJob.get("locations") or None,
        country="FR",
        salary_min=pJob.get("salary_min") or None,
        salary_max=pJob.get("salary_max") or None,
        salary_currency=pJob.get("salary_currency_code") or None,
        salary_period=vPeriod,
        salary_label=pJob.get("salary") or None,
        date=to_iso_date(pJob.get("date")),
        published_at=to_iso_date(pJob.get("date")),
        # Extrait seulement : l'annonce complète est sur le site de l'employeur.
        description=html_to_text(pJob.get("description")),
    )

    return rJob


def parse_jobs(pJobs):
    """Transforme les offres en DataFrame Job."""

    rDataFrame = to_dataframe([parse_job(vJob) for vJob in pJobs])

    return rDataFrame
