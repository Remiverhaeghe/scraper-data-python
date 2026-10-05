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

        rData = {
            "jobs": [
                {
                    "id": 123,
                    "title": "Python Developer"
                }
            ]
        }

        return rData

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


def test_scrape_jobs_respects_max_items(monkeypatch):
    """
    Vérifie que le service Greenhouse respecte max_items.
    """

    # Vérifie que le DataFrame final est limité au nombre demandé.
    def mock_get_jobs(pBoardToken):
        rData = {
            "jobs": [
                {
                    "id": 1,
                    "title": "Python Developer"
                },
                {
                    "id": 2,
                    "title": "Java Developer"
                },
                {
                    "id": 3,
                    "title": "DevOps Engineer"
                },
                {
                    "id": 4,
                    "title": "Software Engineer"
                },
                {
                    "id": 5,
                    "title": "Backend Developer"
                }
            ]
        }

        return rData

    monkeypatch.setattr(
        "job.sources.greenhouse.service.get_jobs",
        mock_get_jobs
    )

    rDataFrame = scrape_jobs(
        "example-board",
        pMaxItems=3
    )

    assert len(rDataFrame) == 3

    assert rDataFrame["title"].tolist() == [
        "Python Developer",
        "Java Developer",
        "DevOps Engineer"
    ]


def test_scrape_jobs_keeps_all_items_without_max_items(
    monkeypatch
):
    """
    Vérifie que toutes les offres sont conservées sans max_items.
    """

    # Vérifie que le comportement historique reste inchangé.
    def mock_get_jobs(pBoardToken):
        rData = {
            "jobs": [
                {
                    "id": 1,
                    "title": "Python Developer"
                },
                {
                    "id": 2,
                    "title": "Java Developer"
                },
                {
                    "id": 3,
                    "title": "DevOps Engineer"
                }
            ]
        }

        return rData

    monkeypatch.setattr(
        "job.sources.greenhouse.service.get_jobs",
        mock_get_jobs
    )

    rDataFrame = scrape_jobs(
        "example-board",
        pMaxItems=None
    )

    assert len(rDataFrame) == 3


def test_scrape_jobs_max_items_greater_than_results(
    monkeypatch
):
    """
    Vérifie qu'une limite supérieure au nombre de résultats
    ne supprime aucune offre.
    """

    # Vérifie qu'une limite suffisamment grande conserve toutes les offres.
    def mock_get_jobs(pBoardToken):
        rData = {
            "jobs": [
                {
                    "id": 1,
                    "title": "Python Developer"
                },
                {
                    "id": 2,
                    "title": "Java Developer"
                }
            ]
        }

        return rData

    monkeypatch.setattr(
        "job.sources.greenhouse.service.get_jobs",
        mock_get_jobs
    )

    rDataFrame = scrape_jobs(
        "example-board",
        pMaxItems=10
    )

    assert len(rDataFrame) == 2