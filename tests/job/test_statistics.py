"""Tests des indicateurs communs au bureau et au web"""

from datetime import date, datetime, timedelta

import pandas as pd
import pytest

from job.settings import save_settings
from job.statistics import (
    MAX_PIE_SOURCES,
    get_source_shares,
    get_week_goal,
    trim_leading_empty_days,
)
from storage.database import initialize_database
from storage.job_applications import save_application
from storage.job_offers import save_offers


def test_get_source_shares_groups_smallest_sources(tmp_path):
    """Vérifie les parts par source et le regroupement des plus petites."""

    vDatabaseFile = tmp_path / "scraper.db"

    initialize_database(vDatabaseFile)

    vSources = (
        ["adzuna"] * 4
        + ["jooble"] * 2
        + [
            "jobicy",
            "himalayas",
            "remotive",
            "arbeitnow",
            "findwork",
        ]
    )

    save_offers(
        vDatabaseFile,
        pd.DataFrame(
            [
                {"source": vSource, "source_id": str(vIndex)}
                for vIndex, vSource in enumerate(vSources)
            ]
        ),
        datetime(2026, 10, 10),
    )

    rShares = get_source_shares(vDatabaseFile)

    assert len(rShares) == MAX_PIE_SOURCES
    assert rShares[0] == {"label": "Adzuna", "count": 4, "percent": 36}
    assert rShares[-1]["label"] == "Autres"
    assert sum(vShare["count"] for vShare in rShares) == len(vSources)


def build_activity(pCounts):
    """Construit une série quotidienne à partir de valeurs, un jour par valeur."""

    rActivity = [
        (date(2026, 10, vDay + 1), vCount) for vDay, vCount in enumerate(pCounts)
    ]

    return rActivity


@pytest.mark.parametrize(
    "pOffers, pApplications, pExpectedDays",
    [
        ([0] * 10 + [5, 0, 0, 2], [0] * 14, 4),
        ([0, 0, 3] + [0] * 11, [0] * 14, 12),
        ([0] * 14, [0] * 12 + [1, 0], 2),
        ([0] * 14, [0] * 14, 1),
    ],
)
def test_trim_leading_empty_days(pOffers, pApplications, pExpectedDays):
    """Vérifie que l'activité démarre au premier jour actif, sans jour vide avant."""

    rActivity = trim_leading_empty_days(
        {
            "new_offers": build_activity(pOffers),
            "applications": build_activity(pApplications),
        }
    )

    assert len(rActivity["new_offers"]) == pExpectedDays
    assert len(rActivity["applications"]) == pExpectedDays


def test_week_goal_counts_applications_since_monday(tmp_path):
    """Vérifie l'objectif de la semaine, compté depuis lundi minuit."""

    vDatabaseFile = tmp_path / "scraper.db"
    vNow = datetime(2026, 10, 21, 15, 0)

    initialize_database(vDatabaseFile)
    save_offers(
        vDatabaseFile,
        pd.DataFrame(
            [
                {"source": "remotive", "source_id": str(vId), "title": "Dev"}
                for vId in range(3)
            ]
        ),
        vNow,
    )

    for vId, vDays in ((0, 3), (1, 1), (2, 0)):
        save_application(
            vDatabaseFile,
            "remotive",
            str(vId),
            "APPLIED",
            pNow=vNow - timedelta(days=vDays),
        )

    assert get_week_goal(vDatabaseFile, vNow)["share"] is None

    save_settings(vDatabaseFile, {"weekly_application_goal": "4"})

    assert get_week_goal(vDatabaseFile, vNow) == {"goal": 4, "sent": 2, "share": 50}
