"""Transformation des offres SmartRecruiters vers le format Job commun"""

import pandas as pd

from job.csv_schema import JOB_COLUMNS, build_job
from utils.helpers import html_to_text

# Parties de l'annonce reprises dans la description, dans cet ordre
DESCRIPTION_SECTIONS = ("jobDescription", "qualifications", "additionalInformation")


def get_label(pValue):
    """Retourne le libellé d'un champ {"id", "label"} de l'API, ou None."""

    rLabel = (pValue or {}).get("label") or None

    return rLabel


def parse_posting(pPosting, pCompany):
    """Transforme une offre de la liste en dictionnaire Job, sans description."""

    vLocation = pPosting.get("location") or {}
    vCountry = vLocation.get("country")

    rJob = build_job(
        title=pPosting.get("name"),
        company=(pPosting.get("company") or {}).get("name") or pCompany,
        source="smartrecruiters",
        source_id=str(pPosting["id"]) if pPosting.get("id") is not None else None,
        url=f"https://jobs.smartrecruiters.com/{pCompany}/{pPosting.get('id')}",
        location=vLocation.get("fullLocation") or vLocation.get("city"),
        city=vLocation.get("city"),
        postal_code=vLocation.get("postalCode"),
        country=vCountry.upper() if vCountry else None,
        contract_type=get_label(pPosting.get("typeOfEmployment")),
        remote=True if vLocation.get("remote") else None,
        remote_type="hybrid" if vLocation.get("hybrid") else None,
        date=pPosting.get("releasedDate"),
        published_at=pPosting.get("releasedDate"),
        # Fonction et secteur aident le filtre par mot-clé avant la lecture du détail.
        department=get_label(pPosting.get("function")),
        job_type=get_label(pPosting.get("industry")),
        experience_level=get_label(pPosting.get("experienceLevel")),
    )

    return rJob


def read_description(pDetail):
    """Retourne le texte de l'annonce, sections réunies, à partir du détail."""

    vSections = (pDetail.get("jobAd") or {}).get("sections") or {}

    rDescription = (
        "\n\n".join(
            vText
            for vName in DESCRIPTION_SECTIONS
            if (vText := html_to_text((vSections.get(vName) or {}).get("text")))
        )
        or None
    )

    return rDescription


def parse_postings(pPostings, pCompany):
    """Transforme une liste d'offres en DataFrame Job."""

    rDataFrame = pd.DataFrame(
        [parse_posting(vPosting, pCompany) for vPosting in pPostings],
        columns=JOB_COLUMNS,
    )

    return rDataFrame
