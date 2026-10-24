"""Tests de la source Workday"""

from datetime import datetime

import pytest

from job.sources.workday import service
from job.sources.workday.client import parse_site
from job.sources.workday.parser import parse_posting, read_posted_date
from job.sources.workday.service import (
    fetch_description,
    find_country_facet,
    scrape_jobs,
)

NOW = datetime(2026, 10, 23, 12, 0)

SITE = parse_site("LFB=lfb.wd3/lfb/LFB_External_Careers")

POSTING = {
    "title": "Technicien de maintenance H/F",
    "externalPath": "/job/Lille-Hauts-de-France/Technicien-de-maintenance_R9955",
    "locationsText": "Lille, Hauts-de-France",
    "postedOn": "Posted 3 Days Ago",
}

# Filtres de lieu regroupés, comme chez Valeo ou Airbus
FACETS = [
    {"facetParameter": "jobFamilyGroup", "values": [{"descriptor": "France"}]},
    {
        "facetParameter": "locationMainGroup",
        "values": [
            {
                "facetParameter": "locationCountry",
                "values": [
                    {"descriptor": "Germany", "id": "de"},
                    {"descriptor": "France", "id": "fr"},
                ],
            }
        ],
    },
]

DETAIL = {
    "jobPostingInfo": {
        "jobDescription": "<p>Maintenance des lignes</p>",
        "timeType": "Full time",
    }
}


def test_site_is_read_with_or_without_name():
    """Vérifie la lecture de « [Nom=]hôte/tenant/site » et le refus d'un autre format."""

    assert SITE.name == "LFB"
    assert SITE.api_url == (
        "https://lfb.wd3.myworkdayjobs.com/wday/cxs/lfb/LFB_External_Careers"
    )
    assert parse_site("valeo.wd3/valeo/valeo_jobs").name == "Valeo"

    with pytest.raises(ValueError):
        parse_site("valeo_jobs")


@pytest.mark.parametrize(
    ("pPostedOn", "pExpected"),
    [
        ("Posted Today", "2026-10-23"),
        ("Posted Yesterday", "2026-10-22"),
        ("Posted 3 Days Ago", "2026-10-20"),
        ("Posted 30+ Days Ago", "2026-09-23"),
        (None, None),
    ],
)
def test_posted_date_is_read_from_its_age(pPostedOn, pExpected):
    """Vérifie la date déduite de l'ancienneté donnée en toutes lettres."""

    assert read_posted_date(pPostedOn, NOW) == pExpected


def test_posting_is_parsed_with_a_unique_identifier():
    """Vérifie l'offre de la liste : identifiant préfixé du tenant, lien public."""

    vJob = parse_posting(POSTING, SITE, NOW)

    assert vJob["source_id"] == "lfb:R9955"
    assert vJob["company"] == "LFB"
    assert vJob["url"] == (
        "https://lfb.wd3.myworkdayjobs.com/LFB_External_Careers"
        "/job/Lille-Hauts-de-France/Technicien-de-maintenance_R9955"
    )
    assert vJob["published_at"] == "2026-10-20"


def test_country_facet_is_found_in_groups():
    """Vérifie la recherche du filtre de pays, même regroupé avec les lieux."""

    assert find_country_facet(FACETS, "France") == ("locationCountry", "fr")
    assert find_country_facet(FACETS[:1], "France") is None


def test_scrape_filters_on_france_and_reads_details(monkeypatch):
    """Vérifie le filtre France demandé à Workday, puis la lecture du détail."""

    vSearches = []

    def search(_pSite, pKeyword, pOffset, pFacets=None):
        vSearches.append((pKeyword, pOffset, pFacets))

        return {"total": 1, "facets": FACETS, "jobPostings": [POSTING]}

    monkeypatch.setattr(service, "search_jobs", search)
    monkeypatch.setattr(service, "get_job", lambda _pSite, pPath: DETAIL)

    vJobs = scrape_jobs("LFB=lfb.wd3/lfb/LFB_External_Careers", "maintenance", pNow=NOW)

    assert vSearches == [
        ("maintenance", 0, None),
        ("maintenance", 0, {"locationCountry": ["fr"]}),
    ]
    assert vJobs.iloc[0]["description"] == "Maintenance des lignes"
    assert vJobs.iloc[0]["employment_type"] == "Full time"


def test_description_is_fetched_from_the_saved_url(monkeypatch):
    """Vérifie la lecture à l'ouverture, site et chemin retrouvés dans l'adresse."""

    vCalls = []
    monkeypatch.setattr(
        service,
        "get_job",
        lambda pSite, pPath: vCalls.append((pSite.site, pPath)) or DETAIL,
    )
    vOffer = {**parse_posting(POSTING, SITE, NOW)}

    assert fetch_description(vOffer) == ("Maintenance des lignes", vOffer["url"])
    assert vCalls == [
        (
            "LFB_External_Careers",
            "/job/Lille-Hauts-de-France/Technicien-de-maintenance_R9955",
        )
    ]
    assert fetch_description({**vOffer, "url": "https://exemple.fr/offre"}) is None


def test_known_workday_offer_is_not_read_again(monkeypatch):
    """Vérifie qu'une offre déjà décrite garde description et temps de travail."""

    monkeypatch.setattr(
        service,
        "search_jobs",
        lambda *_pArgs, **_pOptions: {"total": 1, "jobPostings": [POSTING]},
    )
    monkeypatch.setattr(
        service,
        "get_job",
        lambda *_pArgs: pytest.fail("détail relu alors qu'il est connu"),
    )
    vKnown = {"lfb:R9955": {"description": "En base", "employment_type": "Part time"}}

    vJobs = scrape_jobs("LFB=lfb.wd3/lfb/LFB_External_Careers", pNow=NOW, pKnown=vKnown)

    assert vJobs.iloc[0]["description"] == "En base"
    assert vJobs.iloc[0]["employment_type"] == "Part time"
