"""Transformation des offres Remote OK vers le format Job commun"""

from job.csv_schema import build_job
from job.sources.boards import to_dataframe
from utils.helpers import html_to_text

# Signes d'un texte UTF-8 relu en Latin-1 (« â€“ » pour « – », « Ã© » pour « é »)
MOJIBAKE_MARKS = ("â\x80", "Ã")


def repair_text(pText):
    """Répare un texte UTF-8 mal décodé par la source, sinon le retourne tel quel."""

    rText = pText

    if pText and any(vMark in pText for vMark in MOJIBAKE_MARKS):
        try:
            rText = pText.encode("latin-1").decode("utf-8")
        except UnicodeError:
            rText = pText

    return rText


def parse_job(pJob):
    """Transforme une offre Remote OK en dictionnaire Job."""

    vSalaryMin = pJob.get("salary_min") or None
    vSalaryMax = pJob.get("salary_max") or None

    rJob = build_job(
        title=repair_text(pJob.get("position")),
        company=repair_text(pJob.get("company")),
        source="remoteok",
        source_id=str(pJob["id"]),
        url=pJob.get("url"),
        location=repair_text(pJob.get("location")) or None,
        # Montants annuels en dollars, 0 quand l'offre n'en donne pas
        salary_min=vSalaryMin,
        salary_max=vSalaryMax,
        salary_currency="USD" if vSalaryMin or vSalaryMax else None,
        salary_period="year" if vSalaryMin or vSalaryMax else None,
        remote=True,
        remote_type="full",
        date=pJob.get("date"),
        published_at=pJob.get("date"),
        description=html_to_text(repair_text(pJob.get("description"))),
        skills=", ".join(pJob.get("tags") or []) or None,
    )

    return rJob


def parse_jobs(pJobs):
    """Transforme les offres en DataFrame Job."""

    rDataFrame = to_dataframe([parse_job(vJob) for vJob in pJobs])

    return rDataFrame
