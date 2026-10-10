"""Tests de l'agrégation des offres provenant des différentes sources"""

import pandas as pd

from job.config import JobScrapingConfig
from job.sources.aggregator import scrape_sources


def test_scrape_sources_limits_global_number_of_items(monkeypatch):
    """Vérifie que max_items limite le nombre global d'offres."""

    # Vérifie que plusieurs sources peuvent produire plus d'offres
    # que la limite globale configurée.
    vFranceTravailDataFrame = pd.DataFrame(
        {
            "title": ["FT 1", "FT 2", "FT 3"],
            "source": ["france_travail", "france_travail", "france_travail"],
            "source_id": ["1", "2", "3"],
        }
    )

    vGreenhouseDataFrame = pd.DataFrame(
        {
            "title": ["GH 1", "GH 2"],
            "source": ["greenhouse", "greenhouse"],
            "source_id": ["1", "2"],
        }
    )

    vLeverDataFrame = pd.DataFrame(
        {
            "title": ["Lever 1", "Lever 2"],
            "source": ["lever", "lever"],
            "source_id": ["1", "2"],
        }
    )

    monkeypatch.setattr(
        "job.sources.aggregator.scrape_france_travail",
        lambda pConfig, pParams, pMaxItems=None, pMaxPages=None: vFranceTravailDataFrame,
    )

    monkeypatch.setattr(
        "job.sources.aggregator.scrape_greenhouse",
        lambda pBoard, pMaxItems=None: vGreenhouseDataFrame,
    )

    monkeypatch.setattr(
        "job.sources.aggregator.scrape_lever",
        lambda pSite, pMaxItems=None: vLeverDataFrame,
    )

    vConfig = JobScrapingConfig(max_items=4)

    vConfig.france_travail.enabled = True
    vConfig.france_travail.mode = "api"
    vConfig.france_travail.api_available = True
    vConfig.france_travail.parameters = {"config": object(), "params": {}}

    vConfig.greenhouse.enabled = True
    vConfig.greenhouse.mode = "api"
    vConfig.greenhouse.api_available = True
    vConfig.greenhouse.parameters = {"board": "test-board"}

    vConfig.lever.enabled = True
    vConfig.lever.mode = "api"
    vConfig.lever.api_available = True
    vConfig.lever.parameters = {"site": "test-site"}

    rResult = scrape_sources(vConfig)

    assert len(rResult.items) == 4


def test_scrape_sources_passes_max_items_to_lever(monkeypatch):
    """Vérifie que max_items est transmis au service Lever."""

    # Vérifie que l'agrégateur transmet la limite globale à la source Lever.
    vCalls = []

    vLeverDataFrame = pd.DataFrame(
        {"title": ["Lever 1"], "source": ["lever"], "source_id": ["1"]}
    )

    def mock_scrape_lever(pSite, pMaxItems=None):
        vCalls.append({"site": pSite, "max_items": pMaxItems})

        rDataFrame = vLeverDataFrame

        return rDataFrame

    monkeypatch.setattr("job.sources.aggregator.scrape_lever", mock_scrape_lever)

    vConfig = JobScrapingConfig(max_items=25)

    vConfig.lever.enabled = True
    vConfig.lever.mode = "api"
    vConfig.lever.api_available = True
    vConfig.lever.parameters = {"site": "test-site"}

    rResult = scrape_sources(vConfig)

    assert len(rResult.items) == 1

    assert vCalls == [{"site": "test-site", "max_items": 25}]


def test_scrape_sources_deduplicates_before_applying_limit(monkeypatch):
    """Vérifie que la déduplication est effectuée avant max_items."""

    # Vérifie qu'un doublon ne consomme pas une place dans la limite finale.
    vFranceTravailDataFrame = pd.DataFrame(
        {
            "title": ["Offre 1", "Offre 2"],
            "source": ["france_travail", "france_travail"],
            "source_id": ["1", "2"],
        }
    )

    vGreenhouseDataFrame = pd.DataFrame(
        {
            "title": ["Offre 3", "Offre 4"],
            "source": ["greenhouse", "greenhouse"],
            "source_id": ["1", "2"],
        }
    )

    monkeypatch.setattr(
        "job.sources.aggregator.scrape_france_travail",
        lambda pConfig, pParams, pMaxItems=None, pMaxPages=None: vFranceTravailDataFrame,
    )

    monkeypatch.setattr(
        "job.sources.aggregator.scrape_greenhouse",
        lambda pBoard, pMaxItems=None: vGreenhouseDataFrame,
    )

    vConfig = JobScrapingConfig(max_items=3)

    vConfig.france_travail.enabled = True
    vConfig.france_travail.mode = "api"
    vConfig.france_travail.api_available = True
    vConfig.france_travail.parameters = {"config": object(), "params": {}}

    vConfig.greenhouse.enabled = True
    vConfig.greenhouse.mode = "api"
    vConfig.greenhouse.api_available = True
    vConfig.greenhouse.parameters = {"board": "test-board"}

    rResult = scrape_sources(vConfig)

    assert len(rResult.items) == 3

    assert rResult.items["source_id"].tolist() == ["1", "2", "1"]


def test_scrape_sources_passes_max_items_to_france_travail(monkeypatch):
    """Vérifie que la limite globale est transmise à France Travail."""

    vCalls = []

    vDataFrame = pd.DataFrame(
        {"title": ["Offre Python"], "source": ["france_travail"], "source_id": ["1"]}
    )

    def mock_scrape_france_travail(pConfig, pParams, pMaxItems=None, pMaxPages=None):
        vCalls.append({"config": pConfig, "params": pParams, "max_items": pMaxItems})

        rDataFrame = vDataFrame
        return rDataFrame

    monkeypatch.setattr(
        "job.sources.aggregator.scrape_france_travail", mock_scrape_france_travail
    )

    vConfig = JobScrapingConfig(max_items=25)

    vConfig.france_travail.enabled = True
    vConfig.france_travail.api_available = True
    vConfig.france_travail.mode = "api"

    vFranceTravailConfig = object()

    vFranceTravailParams = {"motsCles": "Python"}

    vConfig.france_travail.parameters = {
        "config": vFranceTravailConfig,
        "params": vFranceTravailParams,
    }

    rResult = scrape_sources(vConfig)

    assert len(rResult.items) == 1

    assert vCalls == [
        {
            "config": vFranceTravailConfig,
            "params": vFranceTravailParams,
            "max_items": 25,
        }
    ]


def test_scrape_sources_passes_max_items_to_greenhouse(monkeypatch):
    """Vérifie que max_items est transmis au service Greenhouse."""

    vCalls = []

    vDataFrame = pd.DataFrame(
        {"title": ["Offre Python"], "source": ["greenhouse"], "source_id": ["1"]}
    )

    def mock_scrape_greenhouse(pBoard, pMaxItems=None):
        vCalls.append({"board": pBoard, "max_items": pMaxItems})

        rDataFrame = vDataFrame
        return rDataFrame

    monkeypatch.setattr(
        "job.sources.aggregator.scrape_greenhouse", mock_scrape_greenhouse
    )

    vConfig = JobScrapingConfig(max_items=25)

    vConfig.greenhouse.enabled = True
    vConfig.greenhouse.mode = "api"
    vConfig.greenhouse.api_available = True
    vConfig.greenhouse.parameters = {"board": "test-board"}

    rResult = scrape_sources(vConfig)

    assert len(rResult.items) == 1

    assert vCalls == [{"board": "test-board", "max_items": 25}]


def test_scrape_sources_passes_max_pages_to_france_travail(monkeypatch):
    """Vérifie que max_pages est transmis au service France Travail."""

    vCalls = []

    vDataFrame = pd.DataFrame(
        {"title": ["Offre Python"], "source": ["france_travail"], "source_id": ["1"]}
    )

    def mock_scrape_france_travail(pConfig, pParams, pMaxItems=None, pMaxPages=None):
        vCalls.append(
            {
                "config": pConfig,
                "params": pParams,
                "max_items": pMaxItems,
                "max_pages": pMaxPages,
            }
        )

        rDataFrame = vDataFrame
        return rDataFrame

    monkeypatch.setattr(
        "job.sources.aggregator.scrape_france_travail", mock_scrape_france_travail
    )

    vConfig = JobScrapingConfig(max_items=25, max_pages=3)

    vConfig.france_travail.enabled = True
    vConfig.france_travail.api_available = True
    vConfig.france_travail.mode = "api"

    vFranceTravailConfig = object()

    vFranceTravailParams = {"motsCles": "Python"}

    vConfig.france_travail.parameters = {
        "config": vFranceTravailConfig,
        "params": vFranceTravailParams,
    }

    rResult = scrape_sources(vConfig)

    assert len(rResult.items) == 1

    assert vCalls == [
        {
            "config": vFranceTravailConfig,
            "params": vFranceTravailParams,
            "max_items": 25,
            "max_pages": 3,
        }
    ]
