"""Tests de l'agrégation des offres provenant des différentes sources"""

import threading

import pandas as pd
import pytest

from job.config import JobScrapingConfig
from job.sources.aggregator import ScrapingCancelled, scrape_sources
from job.sources.config import SourceConfig


def enable_source(pConfig, pName, pParameters):
    """Active une source en mode API avec les paramètres fournis."""

    pConfig.sources[pName] = SourceConfig(
        enabled=True, api_available=True, mode="api", parameters=pParameters
    )


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
        "job.sources.france_travail.source.scrape_jobs",
        lambda pConfig, pParams, pMaxItems=None, pMaxPages=None: vFranceTravailDataFrame,
    )

    monkeypatch.setattr(
        "job.sources.greenhouse.source.scrape_jobs",
        lambda pBoard, pMaxItems=None: vGreenhouseDataFrame,
    )

    monkeypatch.setattr(
        "job.sources.lever.source.scrape_jobs",
        lambda pSite, pMaxItems=None: vLeverDataFrame,
    )

    vConfig = JobScrapingConfig(max_items=4)

    enable_source(vConfig, "france-travail", {"config": object(), "params": {}})

    enable_source(vConfig, "greenhouse", {"board": "test-board"})

    enable_source(vConfig, "lever", {"site": "test-site"})

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

    monkeypatch.setattr("job.sources.lever.source.scrape_jobs", mock_scrape_lever)

    vConfig = JobScrapingConfig(max_items=25)

    enable_source(vConfig, "lever", {"site": "test-site"})

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
        "job.sources.france_travail.source.scrape_jobs",
        lambda pConfig, pParams, pMaxItems=None, pMaxPages=None: vFranceTravailDataFrame,
    )

    monkeypatch.setattr(
        "job.sources.greenhouse.source.scrape_jobs",
        lambda pBoard, pMaxItems=None: vGreenhouseDataFrame,
    )

    vConfig = JobScrapingConfig(max_items=3)

    enable_source(vConfig, "france-travail", {"config": object(), "params": {}})

    enable_source(vConfig, "greenhouse", {"board": "test-board"})

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
        "job.sources.france_travail.source.scrape_jobs", mock_scrape_france_travail
    )

    vConfig = JobScrapingConfig(max_items=25)

    vFranceTravailConfig = object()

    vFranceTravailParams = {"motsCles": "Python"}

    enable_source(
        vConfig,
        "france-travail",
        {"config": vFranceTravailConfig, "params": vFranceTravailParams},
    )

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
        "job.sources.greenhouse.source.scrape_jobs", mock_scrape_greenhouse
    )

    vConfig = JobScrapingConfig(max_items=25)

    enable_source(vConfig, "greenhouse", {"board": "test-board"})

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
        "job.sources.france_travail.source.scrape_jobs", mock_scrape_france_travail
    )

    vConfig = JobScrapingConfig(max_items=25, max_pages=3)

    vFranceTravailConfig = object()

    vFranceTravailParams = {"motsCles": "Python"}

    enable_source(
        vConfig,
        "france-travail",
        {"config": vFranceTravailConfig, "params": vFranceTravailParams},
    )

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


def raise_connection_error(*pArgs, **pKwargs):
    """Simule une source indisponible."""

    raise ConnectionError("API indisponible")


def test_scrape_sources_continues_when_one_source_fails(monkeypatch):
    """Vérifie qu'une source en échec n'empêche pas les autres sources."""

    vLeverDataFrame = pd.DataFrame(
        {"title": ["Lever 1"], "source": ["lever"], "source_id": ["1"]}
    )

    monkeypatch.setattr(
        "job.sources.greenhouse.source.scrape_jobs", raise_connection_error
    )

    monkeypatch.setattr(
        "job.sources.lever.source.scrape_jobs",
        lambda pSite, pMaxItems=None: vLeverDataFrame,
    )

    vConfig = JobScrapingConfig()

    enable_source(vConfig, "greenhouse", {"board": "test-board"})
    enable_source(vConfig, "lever", {"site": "test-site"})

    rResult = scrape_sources(vConfig)

    assert rResult.items["title"].tolist() == ["Lever 1"]
    assert rResult.page_count == 1
    assert rResult.status == "partial"
    assert rResult.error_message == "Greenhouse : API indisponible"


def test_scrape_sources_returns_error_when_all_sources_fail(monkeypatch):
    """Vérifie le statut d'erreur lorsque toutes les sources échouent."""

    monkeypatch.setattr("job.sources.lever.source.scrape_jobs", raise_connection_error)

    vConfig = JobScrapingConfig()

    enable_source(vConfig, "lever", {"site": "test-site"})

    rResult = scrape_sources(vConfig)

    assert rResult.items.empty
    assert rResult.status == "error"
    assert rResult.error_message == "Lever : API indisponible"


def test_scrape_sources_returns_success_without_error(monkeypatch):
    """Vérifie le statut de succès lorsque toutes les sources répondent."""

    monkeypatch.setattr(
        "job.sources.lever.source.scrape_jobs",
        lambda pSite, pMaxItems=None: pd.DataFrame(
            {"title": ["Lever 1"], "source": ["lever"], "source_id": ["1"]}
        ),
    )

    vConfig = JobScrapingConfig()

    enable_source(vConfig, "lever", {"site": "test-site"})

    rResult = scrape_sources(vConfig)

    assert rResult.status == "success"
    assert rResult.error_message is None


def test_scrape_sources_adds_net_salary(monkeypatch):
    """Vérifie que l'agrégation calcule le net mensuel pour toutes les sources."""

    monkeypatch.delenv("INCOME_TAX_RATE", raising=False)

    monkeypatch.setattr(
        "job.sources.lever.source.scrape_jobs",
        lambda pSite, pMaxItems=None: pd.DataFrame(
            {
                "source": ["lever"],
                "source_id": ["1"],
                "salary_min": [48000],
                "salary_currency": ["EUR"],
                "salary_period": ["year"],
            }
        ),
    )

    vConfig = JobScrapingConfig()

    enable_source(vConfig, "lever", {"site": "test-site"})

    rResult = scrape_sources(vConfig)

    assert rResult.items.loc[0, "salary_net_monthly_min"] == 3000


def mock_greenhouse_and_lever(monkeypatch, pCalls):
    """Remplace les services Greenhouse et Lever en mémorisant les appels."""

    def mock_scrape_greenhouse(pBoard, pMaxItems=None):
        pCalls.append("greenhouse")

        rDataFrame = pd.DataFrame(
            {"title": ["GH 1"], "source": ["greenhouse"], "source_id": ["1"]}
        )

        return rDataFrame

    def mock_scrape_lever(pSite, pMaxItems=None):
        pCalls.append("lever")

        rDataFrame = pd.DataFrame(
            {"title": ["Lever 1"], "source": ["lever"], "source_id": ["1"]}
        )

        return rDataFrame

    monkeypatch.setattr(
        "job.sources.greenhouse.source.scrape_jobs", mock_scrape_greenhouse
    )

    monkeypatch.setattr("job.sources.lever.source.scrape_jobs", mock_scrape_lever)


def build_greenhouse_and_lever_config():
    """Construit une configuration avec Greenhouse et Lever activées."""

    vConfig = JobScrapingConfig()

    enable_source(vConfig, "greenhouse", {"board": "test-board"})

    enable_source(vConfig, "lever", {"site": "test-site"})

    rConfig = vConfig

    return rConfig


def test_scrape_sources_reports_progress(monkeypatch):
    """Vérifie que la progression est signalée avant chaque source."""

    vCalls = []
    vProgress = []

    mock_greenhouse_and_lever(monkeypatch, vCalls)

    scrape_sources(
        build_greenhouse_and_lever_config(),
        pOnProgress=lambda pIndex, pTotal, pLabel: vProgress.append(
            (pIndex, pTotal, pLabel)
        ),
    )

    assert vProgress == [(1, 2, "Greenhouse"), (2, 2, "Lever")]


def test_scrape_sources_stops_before_first_source(monkeypatch):
    """Vérifie qu'un arrêt déjà demandé n'interroge aucune source."""

    vCalls = []
    vCancelEvent = threading.Event()
    vCancelEvent.set()

    mock_greenhouse_and_lever(monkeypatch, vCalls)

    with pytest.raises(ScrapingCancelled):
        scrape_sources(build_greenhouse_and_lever_config(), pCancelEvent=vCancelEvent)

    assert vCalls == []


def test_scrape_sources_stops_between_sources(monkeypatch):
    """Vérifie qu'un arrêt demandé pendant une source empêche la suivante."""

    vCalls = []
    vCancelEvent = threading.Event()

    mock_greenhouse_and_lever(monkeypatch, vCalls)

    monkeypatch.setattr(
        "job.sources.greenhouse.source.scrape_jobs",
        lambda pBoard, pMaxItems=None: vCancelEvent.set() or pd.DataFrame(),
    )

    with pytest.raises(ScrapingCancelled):
        scrape_sources(build_greenhouse_and_lever_config(), pCancelEvent=vCancelEvent)

    assert vCalls == []
