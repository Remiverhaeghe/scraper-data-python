# ============================================================================
# Tests du service France Travail
# ============================================================================

import pandas as pd

from job.sources.france_travail.service import scrape_jobs


class FakeConfig:
    """
    Configuration fictive utilisée par les tests.
    """

    pass


def test_scrape_jobs(monkeypatch):
    """
    Vérifie l'orchestration client → parser.
    """

    vData = {
        "resultats": [
            {
                "id": "123",
                "intitule": "Développeur Python"
            }
        ]
    }

    def mock_search_jobs(pConfig, pParams):
        assert isinstance(
            pConfig,
            FakeConfig
        )
        assert pParams == {
            "motsCles": "python"
        }

        return vData

    monkeypatch.setattr(
        "job.sources.france_travail.service.search_jobs",
        mock_search_jobs
    )

    rDataFrame = scrape_jobs(
        FakeConfig(),
        {
            "motsCles": "python"
        }
    )

    assert isinstance(
        rDataFrame,
        pd.DataFrame
    )

    assert len(rDataFrame) == 1
    assert rDataFrame.iloc[0]["title"] == (
        "Développeur Python"
    )


def test_scrape_jobs_without_results(monkeypatch):
    """
    Vérifie le comportement lorsqu'aucune offre n'est retournée.
    """

    def mock_search_jobs(pConfig, pParams):
        return {}

    monkeypatch.setattr(
        "job.sources.france_travail.service.search_jobs",
        mock_search_jobs
    )

    rDataFrame = scrape_jobs(
        FakeConfig(),
        {}
    )

    assert isinstance(
        rDataFrame,
        pd.DataFrame
    )

    assert rDataFrame.empty