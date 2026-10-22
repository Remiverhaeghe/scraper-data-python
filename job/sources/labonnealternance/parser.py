"""Transformation des offres La bonne alternance vers le format Job commun"""

from job.csv_schema import build_job
from job.sources.boards import to_dataframe
from utils.helpers import html_to_text


def join_values(pValue):
    """Retourne une liste de libellés en texte, ou le texte tel quel."""

    rText = (
        ", ".join(str(vItem) for vItem in pValue if vItem)
        if isinstance(pValue, list)
        else pValue
    ) or None

    return rText


def parse_job(pJob):
    """Transforme une offre en dictionnaire Job.

    L'offre est découpée en blocs : identifiant, entreprise, lieu, contrat,
    offre, publication et candidature.
    """

    vIdentifier = pJob.get("identifier") or {}
    vWorkplace = pJob.get("workplace") or {}
    vLocation = pJob.get("location") or {}
    vContract = pJob.get("contract") or {}
    vOffer = pJob.get("offer") or {}
    vPublication = pJob.get("publication") or {}
    vDuration = vContract.get("duration")

    rJob = build_job(
        title=vOffer.get("title"),
        company=(
            vWorkplace.get("brand")
            or vWorkplace.get("name")
            or vWorkplace.get("legal_name")
        ),
        source="labonnealternance",
        source_id=str(vIdentifier.get("id")) if vIdentifier.get("id") else None,
        url=(pJob.get("apply") or {}).get("url"),
        location=vLocation.get("address"),
        country="FR",
        contract_type=join_values(vContract.get("type")) or "Alternance",
        employment_type=f"{vDuration} mois" if vDuration else None,
        date=vPublication.get("creation"),
        published_at=vPublication.get("creation"),
        description=html_to_text(vOffer.get("description")),
        requirements=join_values(vOffer.get("desired_skills")),
        education=join_values(vOffer.get("target_diploma")),
        job_type=join_values(vIdentifier.get("partner_label")),
    )

    return rJob


def parse_jobs(pJobs):
    """Transforme les offres en DataFrame Job."""

    rDataFrame = to_dataframe([parse_job(vJob) for vJob in pJobs])

    return rDataFrame
