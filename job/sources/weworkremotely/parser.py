"""Transformation du flux We Work Remotely vers le format Job commun"""

from email.utils import parsedate_to_datetime

from job.csv_schema import build_job
from job.sources.boards import to_dataframe
from utils.helpers import html_to_text


def read(pItem, pTag):
    """Retourne le texte d'une balise de l'offre, ou None si elle est vide."""

    rText = (pItem.findtext(pTag) or "").strip() or None

    return rText


def to_iso_date(pDate):
    """Convertit une date RSS (« Wed, 21 Oct 2026 14:00:00 +0000 ») au format ISO."""

    try:
        rDate = parsedate_to_datetime(pDate).isoformat() if pDate else None
    except (TypeError, ValueError):
        rDate = None

    return rDate


def parse_item(pItem):
    """Transforme un élément du flux en dictionnaire Job.

    Le titre suit la forme « Entreprise: Poste ».
    """

    vCompany, vSeparator, vTitle = (read(pItem, "title") or "").partition(": ")
    vLink = read(pItem, "link")

    rJob = build_job(
        title=vTitle if vSeparator else vCompany,
        company=vCompany if vSeparator else None,
        source="weworkremotely",
        source_id=read(pItem, "guid") or vLink,
        url=vLink,
        location=read(pItem, "region") or read(pItem, "country"),
        contract_type=read(pItem, "type"),
        remote=True,
        remote_type="full",
        date=to_iso_date(read(pItem, "pubDate")),
        published_at=to_iso_date(read(pItem, "pubDate")),
        description=html_to_text(read(pItem, "description")),
        skills=read(pItem, "skills"),
        job_type=read(pItem, "category"),
    )

    return rJob


def parse_items(pItems):
    """Transforme les éléments du flux en DataFrame Job."""

    rDataFrame = to_dataframe([parse_item(vItem) for vItem in pItems])

    return rDataFrame
