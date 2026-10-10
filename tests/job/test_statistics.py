"""Tests des indicateurs communs au bureau et au web"""

from datetime import datetime

import pandas as pd

from job.statistics import MAX_PIE_SOURCES, get_source_shares
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
