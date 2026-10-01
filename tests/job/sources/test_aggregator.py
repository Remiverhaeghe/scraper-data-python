# ============================================================================
# Tests de l'agrégateur des sources d'emploi
# ============================================================================

import pandas as pd

from unittest.mock import patch
from job.config import JobScrapingConfig
from job.csv_schema import JOB_COLUMNS
from job.sources.aggregator import scrape_sources
from job.sources.config import SourceConfig
from scraper.result import ScrapingResult


def test_scrape_sources(monkeypatch):
    """
    Vérifie l'agrégation de plusieurs sources activées.
    """

    vFranceTravail = pd.DataFrame(
        [
            {
                "title": "Développeur Python",
                "source": "france_travail",
                "source_id": "ft-1"
            }
        ],
        columns=JOB_COLUMNS
    )

    vGreenhouse = pd.DataFrame(
        [
            {
                "title": "Développeur Java",
                "source": "greenhouse",
                "source_id": "gh-1"
            }
        ],
        columns=JOB_COLUMNS
    )

    vLever = pd.DataFrame(
        [
            {
                "title": "DevOps Engineer",
                "source": "lever",
                "source_id": "lv-1"
            }
        ],
        columns=JOB_COLUMNS
    )

    def mock_france_travail(pConfig, pParams):
        return vFranceTravail

    def mock_greenhouse(pBoard):
        return vGreenhouse

    def mock_lever(pSite):
        return vLever

    monkeypatch.setattr(
        "job.sources.aggregator.scrape_france_travail",
        mock_france_travail
    )

    monkeypatch.setattr(
        "job.sources.aggregator.scrape_greenhouse",
        mock_greenhouse
    )

    monkeypatch.setattr(
        "job.sources.aggregator.scrape_lever",
        mock_lever
    )

    vConfig = JobScrapingConfig(
        france_travail=SourceConfig(
            enabled=True,
            api_available=True,
            mode="api",
            parameters={
                "config": "config",
                "params": {
                    "motCle": "python"
                }
            }
        ),
        greenhouse=SourceConfig(
            enabled=True,
            api_available=True,
            mode="api",
            parameters={
                "board": "example-board"
            }
        ),
        lever=SourceConfig(
            enabled=True,
            api_available=True,
            mode="api",
            parameters={
                "site": "example-company"
            }
        )
    )

    rResult = scrape_sources(
        vConfig
    )

    assert isinstance(
        rResult,
        ScrapingResult
    )

    assert len(rResult.items) == 3

    assert list(rResult.items.columns) == JOB_COLUMNS

    assert list(rResult.items["source"]) == [
        "france_travail",
        "greenhouse",
        "lever"
    ]

    assert rResult.page_count == 3
    assert rResult.duration_seconds >= 0
    assert rResult.started_at is not None
    assert rResult.status == "success"
    assert rResult.error_message is None


def test_scrape_sources_without_sources():
    """
    Vérifie qu'aucune source ne produit un résultat vide structuré.
    """

    vConfig = JobScrapingConfig()

    rResult = scrape_sources(
        vConfig
    )

    assert isinstance(
        rResult,
        ScrapingResult
    )

    assert rResult.items.empty
    assert list(rResult.items.columns) == JOB_COLUMNS
    assert rResult.page_count == 0
    assert rResult.duration_seconds >= 0
    assert rResult.started_at is not None


def test_scrape_sources_with_one_source(monkeypatch):
    """
    Vérifie qu'une seule source peut être utilisée.
    """

    vDataFrame = pd.DataFrame(
        [
            {
                "title": "Python Developer",
                "source": "lever",
                "source_id": "lv-1"
            }
        ],
        columns=JOB_COLUMNS
    )

    def mock_lever(pSite):
        return vDataFrame

    monkeypatch.setattr(
        "job.sources.aggregator.scrape_lever",
        mock_lever
    )

    vConfig = JobScrapingConfig(
        lever=SourceConfig(
            enabled=True,
            api_available=True,
            mode="api",
            parameters={
                "site": "example-company"
            }
        )
    )

    rResult = scrape_sources(
        vConfig
    )

    assert isinstance(
        rResult,
        ScrapingResult
    )

    assert len(rResult.items) == 1

    assert rResult.items.iloc[0]["title"] == (
        "Python Developer"
    )

    assert rResult.items.iloc[0]["source"] == "lever"

    assert rResult.page_count == 1


def test_scrape_sources_does_not_call_disabled_sources(
    monkeypatch
):
    """
    Vérifie qu'une source désactivée n'est jamais appelée.
    """

    vCalled = {
        "lever": False
    }

    def mock_lever(pSite):
        vCalled["lever"] = True

        return pd.DataFrame(
            columns=JOB_COLUMNS
        )

    monkeypatch.setattr(
        "job.sources.aggregator.scrape_lever",
        mock_lever
    )

    vConfig = JobScrapingConfig()

    rResult = scrape_sources(
        vConfig
    )

    assert rResult.items.empty
    assert not vCalled["lever"]

# ============================================================================
# Tests de déduplication lors de l'agrégation
# ============================================================================

def test_scrape_sources_removes_duplicate_from_same_source():
    """
    Vérifie qu'une même offre provenant deux fois de la même source
    n'est conservée qu'une seule fois.
    """

    vConfig = JobScrapingConfig(
        france_travail=SourceConfig(
            enabled=False
        ),
        greenhouse=SourceConfig(
            enabled=False
        ),
        lever=SourceConfig(
            enabled=True,
            api_available=True,
            mode="api",
            parameters={
                "site": "test"
            }
        )
    )

    vJobs = pd.DataFrame(
        [
            {
                "source": "lever",
                "source_id": "job-1",
                "title": "Développeur Python"
            },
            {
                "source": "lever",
                "source_id": "job-1",
                "title": "Développeur Python"
            }
        ]
    )

    with patch(
        "job.sources.aggregator.scrape_lever",
        return_value=vJobs
    ):
        rResult = scrape_sources(vConfig)

    assert len(rResult.items) == 1
    assert rResult.items.iloc[0]["source_id"] == "job-1"


def test_scrape_sources_keeps_same_source_id_from_different_sources():
    """
    Vérifie qu'un même identifiant provenant de deux sources différentes
    n'est pas considéré comme un doublon.
    """

    vConfig = JobScrapingConfig(
        france_travail=SourceConfig(
            enabled=False
        ),
        greenhouse=SourceConfig(
            enabled=True,
            api_available=True,
            mode="api",
            parameters={
                "board": "test"
            }
        ),
        lever=SourceConfig(
            enabled=True,
            api_available=True,
            mode="api",
            parameters={
                "site": "test"
            }
        )
    )

    vGreenhouseJobs = pd.DataFrame(
        [
            {
                "source": "greenhouse",
                "source_id": "job-1",
                "title": "Développeur Python"
            }
        ]
    )

    vLeverJobs = pd.DataFrame(
        [
            {
                "source": "lever",
                "source_id": "job-1",
                "title": "Développeur Python"
            }
        ]
    )

    with patch(
        "job.sources.aggregator.scrape_greenhouse",
        return_value=vGreenhouseJobs
    ), patch(
        "job.sources.aggregator.scrape_lever",
        return_value=vLeverJobs
    ):
        rResult = scrape_sources(vConfig)

    assert len(rResult.items) == 2
    assert set(rResult.items["source"]) == {
        "greenhouse",
        "lever"
    }

def test_scrape_sources_keeps_jobs_without_source_id():
    """
    Vérifie que les offres sans identifiant source
    sont conservées individuellement.
    """

    vConfig = JobScrapingConfig(
        lever=SourceConfig(
            enabled=True,
            api_available=True,
            mode="api",
            parameters={
                "site": "test"
            }
        )
    )

    vJobs = pd.DataFrame(
        [
            {
                "source": "lever",
                "source_id": None,
                "title": "Développeur Python"
            },
            {
                "source": "lever",
                "source_id": None,
                "title": "Développeur Java"
            }
        ]
    )

    with patch(
        "job.sources.aggregator.scrape_lever",
        return_value=vJobs
    ):
        rResult = scrape_sources(vConfig)

    assert len(rResult.items) == 2
    assert set(rResult.items["title"]) == {
        "Développeur Python",
        "Développeur Java"
    }