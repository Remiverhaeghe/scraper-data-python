"""Tests des indicateurs communs au bureau et au web"""

from datetime import date, datetime

import pandas as pd
import pytest

from job.statistics import MAX_PIE_SOURCES, get_source_shares, trim_leading_empty_days
from storage.database import initialize_database
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
        ([0] * 10 + [5, 0, 0, 2], [0] * 14, 7),
        ([0, 0, 3] + [0] * 11, [0] * 14, 12),
        ([0] * 14, [0] * 13 + [1], 7),
        ([0] * 14, [0] * 14, 7),
    ],
)
def test_trim_leading_empty_days(pOffers, pApplications, pExpectedDays):
    """Vérifie que l'activité démarre au premier jour actif, sur 7 jours au moins."""

    rActivity = trim_leading_empty_days(
        {
            "new_offers": build_activity(pOffers),
            "applications": build_activity(pApplications),
        }
    )

    assert len(rActivity["new_offers"]) == pExpectedDays
    assert len(rActivity["applications"]) == pExpectedDays
