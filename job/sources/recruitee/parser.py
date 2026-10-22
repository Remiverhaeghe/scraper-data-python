"""Transformation des offres Recruitee vers le format Job commun"""

from job.csv_schema import build_job
from job.sources.boards import to_dataframe
from utils.helpers import html_to_text


def parse_offer(pOffer, pCompany):
    """Transforme une offre Recruitee en dictionnaire Job."""

    vDescription = "\n\n".join(
        vText
        for vHtml in (pOffer.get("description"), pOffer.get("requirements"))
        if (vText := html_to_text(vHtml))
    )
    vSalary = pOffer.get("salary") or {}

    rJob = build_job(
        title=pOffer.get("title"),
        company=pOffer.get("company_name") or pCompany,
        source="recruitee",
        source_id=str(pOffer["id"]) if pOffer.get("id") is not None else None,
        url=pOffer.get("careers_url"),
        location=pOffer.get("location"),
        city=pOffer.get("city"),
        postal_code=pOffer.get("postal_code"),
        country=pOffer.get("country_code"),
        contract_type=pOffer.get("employment_type_code"),
        salary_min=vSalary.get("min"),
        salary_max=vSalary.get("max"),
        salary_currency=vSalary.get("currency"),
        remote=True if pOffer.get("remote") else None,
        remote_type="hybrid" if pOffer.get("hybrid") else None,
        date=pOffer.get("published_at"),
        published_at=pOffer.get("published_at"),
        description=vDescription or None,
        department=pOffer.get("department"),
    )

    return rJob


def parse_offers(pOffers, pCompany):
    """Transforme les offres d'une entreprise en DataFrame Job."""

    rDataFrame = to_dataframe([parse_offer(vOffer, pCompany) for vOffer in pOffers])

    return rDataFrame
