"""Transformation des offres Lever vers le format Job commun"""

from datetime import datetime, timezone

from job.csv_schema import build_job
from job.sources.boards import to_country_code, to_dataframe


def to_iso_date(pMilliseconds):
    """Convertit une date Lever, en millisecondes depuis 1970, au format ISO."""

    rDate = (
        datetime.fromtimestamp(pMilliseconds / 1000, timezone.utc).isoformat()
        if isinstance(pMilliseconds, (int, float))
        else None
    )

    return rDate


def parse_posting(pPosting, pCompany):
    """Transforme une offre Lever en dictionnaire Job."""

    vCategories = pPosting.get("categories") or {}
    vDescription = "\n\n".join(
        vPart
        for vPart in (pPosting.get("descriptionPlain"), pPosting.get("additionalPlain"))
        if vPart
    )
    vWorkplace = pPosting.get("workplaceType")

    rJob = build_job(
        title=pPosting.get("text"),
        # « acme-corp » devient « Acme Corp » : Lever ne nomme pas l'entreprise.
        company=pCompany.replace("-", " ").title(),
        source="lever",
        source_id=pPosting.get("id"),
        url=pPosting.get("hostedUrl"),
        location=vCategories.get("location"),
        country=to_country_code(pPosting.get("country")),
        contract_type=vCategories.get("commitment"),
        remote=True if vWorkplace == "remote" else None,
        remote_type=vWorkplace if vWorkplace in ("remote", "hybrid") else None,
        date=to_iso_date(pPosting.get("createdAt")),
        published_at=to_iso_date(pPosting.get("createdAt")),
        description=vDescription or None,
        department=vCategories.get("department") or vCategories.get("team"),
    )

    return rJob


def parse_postings(pPostings, pCompany):
    """Transforme les offres d'une entreprise en DataFrame Job."""

    rDataFrame = to_dataframe(
        [parse_posting(vPosting, pCompany) for vPosting in pPostings]
    )

    return rDataFrame
