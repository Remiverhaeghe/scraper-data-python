"""Tests des recherches enregistrées"""

from datetime import datetime

import pytest

from storage.database import initialize_database
from storage.saved_searches import (
    MAX_NAME_LENGTH,
    delete_saved_search,
    get_saved_searches,
    save_search,
)

NOW = datetime(2026, 10, 11, 9, 0)


@pytest.fixture
def database_file(tmp_path):
    """Crée une base vide."""

    rDatabaseFile = tmp_path / "scraper.db"

    initialize_database(rDatabaseFile)

    return rDatabaseFile


def test_saved_searches_are_listed_replaced_and_deleted(database_file):
    """Vérifie l'enregistrement, le tri, le remplacement et la suppression."""

    save_search(database_file, " Java Lille ", ["adzuna"], {"keyword": "Java"}, NOW)
    save_search(database_file, "alternance", ["remotive"], {}, NOW)
    save_search(database_file, "Java Lille", ["jooble"], {"keyword": "Kotlin"}, NOW)

    vSearches = get_saved_searches(database_file)

    assert [vSearch["name"] for vSearch in vSearches] == ["alternance", "Java Lille"]
    assert vSearches[1] == {
        "name": "Java Lille",
        "sources": ["jooble"],
        "criteria": {"keyword": "Kotlin"},
    }

    delete_saved_search(database_file, "alternance")

    assert [vSearch["name"] for vSearch in get_saved_searches(database_file)] == [
        "Java Lille"
    ]


@pytest.mark.parametrize("pName", ["", "   ", "x" * (MAX_NAME_LENGTH + 1)])
def test_save_search_rejects_invalid_names(database_file, pName):
    """Vérifie le refus d'un nom vide ou trop long."""

    with pytest.raises(ValueError):
        save_search(database_file, pName, ["adzuna"], {}, NOW)
