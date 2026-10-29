"""Tests des recherches prêtes à l'emploi"""

from datetime import datetime

import pytest

from job.geocoding import HOME_KEY
from job.search_presets import (
    INDUSTRY_KEYWORDS,
    LOCAL_KEYWORDS,
    create_industry_searches,
    create_local_searches,
)
from job.sources.registry import SOURCES
from storage.database import initialize_database
from storage.saved_searches import get_saved_searches
from storage.settings_repository import save_json_setting


def test_industry_searches_use_france_and_company_pages(tmp_path):
    """Vérifie les trois recherches Industrie, leurs sources et leur mot-clé."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)

    vNames = create_industry_searches(vDatabaseFile, datetime(2026, 10, 22))
    create_industry_searches(vDatabaseFile, datetime(2026, 10, 23))

    vSearches = {
        vSearch["name"]: vSearch for vSearch in get_saved_searches(vDatabaseFile)
    }

    assert vNames == [f"Industrie · {vKeyword}" for vKeyword in INDUSTRY_KEYWORDS]
    assert "Industrie · Maintenance ferroviaire" in vNames
    assert len(vSearches) == len(INDUSTRY_KEYWORDS)
    assert vSearches["Industrie · Automatisme"]["criteria"]["keyword"] == "automatisme"
    assert {SOURCES[vName].category for vName in vSearches[vNames[0]]["sources"]} == {
        "france",
        "company",
    }


def test_local_searches_use_home_city_and_radius(tmp_path):
    """Vérifie les recherches autour du domicile, refusées sans domicile."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)

    with pytest.raises(ValueError):
        create_local_searches(vDatabaseFile, datetime(2026, 10, 23))

    save_json_setting(
        vDatabaseFile,
        HOME_KEY,
        {"label": "Rue A 59100 Roubaix", "latitude": 50.69, "longitude": 3.18},
    )
    vNames = create_local_searches(vDatabaseFile, datetime(2026, 10, 23))
    vCriteria = get_saved_searches(vDatabaseFile)[0]["criteria"]

    assert vNames[0] == "Près de chez moi · Java"
    assert len(vNames) == len(LOCAL_KEYWORDS)
    assert vCriteria["location"] == "Roubaix"
    assert vCriteria["max_distance_km"] == 30
