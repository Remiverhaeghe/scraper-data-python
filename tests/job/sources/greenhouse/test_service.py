# ============================================================================
# Tests du service Greenhouse
# ============================================================================

import pandas as pd

from job.sources.greenhouse.service import scrape_jobs


def test_scrape_jobs(monkeypatch):
    """
    Vérifie l'orchestration client → parser.
    """

    def mock_get_jobs(pBoardToken):
        assert pBoardToken == "example-board"

        return {
            "jobs": [
                {
                    "id": 123,
                    "title": "Python Developer"
                }
            ]
        }

    monkeypatch.setattr(
        "job.sources.greenhouse.service.get_jobs",
        mock_get_jobs
    )

    rDataFrame = scrape_jobs(
        "example-board"
    )

    assert isinstance(
        rDataFrame,
        pd.DataFrame
    )

    assert len(rDataFrame) == 1
    assert rDataFrame.iloc[0]["title"] == (
        "Python Developer"
    )
    assert rDataFrame.iloc[0]["source"] == (
        "greenhouse"
    )


def test_scrape_jobs_without_results(monkeypatch):
    """
    Vérifie le comportement sans résultat.
    """

    monkeypatch.setattr(
        "job.sources.greenhouse.service.get_jobs",
        lambda pBoardToken: {}
    )

    rDataFrame = scrape_jobs(
        "example-board"
    )

    assert isinstance(
        rDataFrame,
        pd.DataFrame
    )

    assert rDataFrame.empty