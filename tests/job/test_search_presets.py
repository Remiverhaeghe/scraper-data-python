"""Tests des recherches prêtes à l'emploi"""

from datetime import datetime

from job.search_presets import create_industry_searches
from job.sources.registry import SOURCES
from storage.database import initialize_database
from storage.saved_searches import get_saved_searches


def test_industry_searches_use_france_and_company_pages(tmp_path):
    """Vérifie les trois recherches Industrie, leurs sources et leur mot-clé."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)

    vNames = create_industry_searches(vDatabaseFile, datetime(2026, 10, 22))
    create_industry_searches(vDatabaseFile, datetime(2026, 10, 23))

    vSearches = {
        vSearch["name"]: vSearch for vSearch in get_saved_searches(vDatabaseFile)
    }

    assert vNames == [
        "Industrie · Maintenance",
        "Industrie · Automatisme",
        "Industrie · Électrotechnique",
    ]
    assert len(vSearches) == 3
    assert vSearches["Industrie · Automatisme"]["criteria"]["keyword"] == "automatisme"
    assert {SOURCES[vName].category for vName in vSearches[vNames[0]]["sources"]} == {
        "france",
        "company",
    }
