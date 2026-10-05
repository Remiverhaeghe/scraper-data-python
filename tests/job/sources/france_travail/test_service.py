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

    def mock_search_jobs(
        pConfig,
        pParams
    ):
        assert isinstance(
            pConfig,
            FakeConfig
        )

        assert pParams == {
            "motsCles": "python"
        }

        rData = vData
        return rData

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

    def mock_search_jobs(
        pConfig,
        pParams
    ):
        rData = {}
        return rData

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


def test_scrape_jobs_respects_max_items(monkeypatch):
    """
    Vérifie que le nombre maximum d'offres est respecté.
    """

    vData = {
        "resultats": [
            {
                "id": "1",
                "intitule": "Développeur Python"
            },
            {
                "id": "2",
                "intitule": "Développeur Java"
            },
            {
                "id": "3",
                "intitule": "DevOps"
            },
            {
                "id": "4",
                "intitule": "Software Engineer"
            },
            {
                "id": "5",
                "intitule": "Backend Developer"
            }
        ]
    }

    def mock_search_jobs(
        pConfig,
        pParams
    ):
        rData = vData
        return rData

    monkeypatch.setattr(
        "job.sources.france_travail.service.search_jobs",
        mock_search_jobs
    )

    rDataFrame = scrape_jobs(
        FakeConfig(),
        {},
        pMaxItems=3
    )

    assert len(rDataFrame) == 3

    assert rDataFrame["title"].tolist() == [
        "Développeur Python",
        "Développeur Java",
        "DevOps"
    ]


def test_scrape_jobs_keeps_all_items_without_max_items(
    monkeypatch
):
    """
    Vérifie que toutes les offres sont conservées sans limite.
    """

    vData = {
        "resultats": [
            {
                "id": "1",
                "intitule": "Développeur Python"
            },
            {
                "id": "2",
                "intitule": "Développeur Java"
            },
            {
                "id": "3",
                "intitule": "DevOps"
            }
        ]
    }

    def mock_search_jobs(
        pConfig,
        pParams
    ):
        rData = vData
        return rData

    monkeypatch.setattr(
        "job.sources.france_travail.service.search_jobs",
        mock_search_jobs
    )

    rDataFrame = scrape_jobs(
        FakeConfig(),
        {},
        pMaxItems=None
    )

    assert len(rDataFrame) == 3


def test_scrape_jobs_max_items_greater_than_results(
    monkeypatch
):
    """
    Vérifie qu'une limite supérieure au nombre de résultats
    conserve toutes les offres.
    """

    vData = {
        "resultats": [
            {
                "id": "1",
                "intitule": "Développeur Python"
            },
            {
                "id": "2",
                "intitule": "Développeur Java"
            }
        ]
    }

    def mock_search_jobs(
        pConfig,
        pParams
    ):
        rData = vData
        return rData

    monkeypatch.setattr(
        "job.sources.france_travail.service.search_jobs",
        mock_search_jobs
    )

    rDataFrame = scrape_jobs(
        FakeConfig(),
        {},
        pMaxItems=10
    )

    assert len(rDataFrame) == 2