"""Tests du suivi des pages lentes"""

from datetime import datetime, timedelta

import pytest

from job.page_timings import (
    KEPT_PER_PAGE,
    SLOW_PAGES_KEY,
    describe_slow_pages,
    find_slow_pages,
    load_slow_pages,
    record_page_time,
)
from storage.database import initialize_database
from storage.settings_repository import load_json_setting, save_json_setting

NOW = datetime(2026, 10, 31, 12, 0)


@pytest.fixture
def database_file(tmp_path):
    """Crée une base vide."""

    rDatabaseFile = tmp_path / "scraper.db"

    initialize_database(rDatabaseFile)

    return rDatabaseFile


def test_fast_page_is_not_kept(database_file, caplog):
    """Vérifie qu'une page rapide n'est ni journalisée ni gardée."""

    record_page_time(database_file, "bureau offers", 0.4, NOW)

    assert "Page lente" not in caplog.text
    assert load_json_setting(database_file, SLOW_PAGES_KEY, {}) == {}


def test_page_is_reported_after_three_slow_loads(database_file):
    """Vérifie qu'une page n'est signalée qu'après trois dépassements de 2 s."""

    record_page_time(database_file, "site /offers", 1.5, NOW)
    record_page_time(database_file, "site /offers", 2.4, NOW)
    record_page_time(database_file, "site /offers", 3.1, NOW)

    assert load_slow_pages(database_file, NOW) == []

    record_page_time(database_file, "site /offers", 2.2, NOW)

    vPages = load_slow_pages(database_file, NOW)

    assert vPages == [{"page": "site /offers", "count": 3, "max": 3.1}]
    assert describe_slow_pages(vPages) == "site /offers (3 fois, jusqu'à 3.1 s)"


def test_old_and_surplus_durations_are_dropped(database_file):
    """Vérifie que seules les durées de la semaine et les dernières sont gardées."""

    vOld = (NOW - timedelta(days=8)).isoformat()
    save_json_setting(
        database_file, SLOW_PAGES_KEY, {"bureau market": [[vOld, 5.0]] * 3}
    )

    for _ in range(KEPT_PER_PAGE + 5):
        record_page_time(database_file, "bureau skills", 1.2, NOW)

    vTimings = load_json_setting(database_file, SLOW_PAGES_KEY, {})

    assert list(vTimings) == ["bureau skills"]
    assert len(vTimings["bureau skills"]) == KEPT_PER_PAGE


def test_slowest_page_comes_first():
    """Vérifie l'ordre des pages signalées et le rejet d'une entrée mal formée."""

    vDay = NOW.isoformat()
    vPages = find_slow_pages(
        {
            "bureau offers": [[vDay, 2.5]] * 3,
            "site /": [[vDay, 4.0]] * 3 + ["illisible"],
        },
        NOW,
    )

    assert [vPage["page"] for vPage in vPages] == ["site /", "bureau offers"]


def test_storage_error_does_not_break_the_page(database_file, monkeypatch, caplog):
    """Vérifie qu'une base illisible est journalisée sans lever d'erreur."""

    def fail(*pArgs):
        raise OSError("disque")

    monkeypatch.setattr("job.page_timings.save_json_setting", fail)

    record_page_time(database_file, "bureau offers", 3.0, NOW)

    assert "Impossible de garder la durée de la page bureau offers" in caplog.text
