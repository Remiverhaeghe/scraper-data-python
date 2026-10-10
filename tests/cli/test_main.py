"""Tests du point d'entrée du mode ligne de commande"""

from dataclasses import replace

import pytest

import cli.main as main
from job.sources.registry import SOURCES


@pytest.fixture
def france_travail_available(monkeypatch):
    """Rend France Travail disponible le temps d'un test."""

    monkeypatch.setitem(
        SOURCES, "france-travail", replace(SOURCES["france-travail"], available=True)
    )


# Configuration des sources pour les tests


def set_job_sources_environment(pMonkeypatch):
    """Configure les variables d'environnement fictives des sources d'emploi."""

    pMonkeypatch.setenv("FRANCE_TRAVAIL_CLIENT_ID", "test-client-id")

    pMonkeypatch.setenv("FRANCE_TRAVAIL_CLIENT_SECRET", "test-client-secret")

    pMonkeypatch.setenv("FRANCE_TRAVAIL_SCOPE", "test-scope")

    pMonkeypatch.setenv("FRANCE_TRAVAIL_TOKEN_URL", "https://test.example/token")

    pMonkeypatch.setenv("FRANCE_TRAVAIL_API_BASE_URL", "https://test.example/api/")

    pMonkeypatch.setenv("GREENHOUSE_BOARD", "test-board")

    pMonkeypatch.setenv("LEVER_SITE", "test-site")


# Tests du traitement des livres


def test_main_processes_books(monkeypatch):
    """Vérifie que le mode CLI lance le traitement des livres."""

    vCalls = []

    vArguments = type(
        "Arguments",
        (),
        {
            "type": "book",
            "max_items": 100,
            "delay": 1.0,
            "timeout": 30,
            "max_pages": 2,
            "title": "python",
            "max_price": 20,
            "min_rating": 4,
            "refresh": True,
        },
    )()

    def mock_parse_arguments():
        """Simule la lecture des arguments."""

        vCalls.append("parse_arguments")

        return vArguments

    def mock_process_books(pUrl, pOutputFile, pConfig, pRefresh):
        """Simule le traitement complet des livres."""

        vCalls.append("process_books")

        assert pConfig.max_items == 100
        assert pConfig.delay == 1.0
        assert pConfig.timeout == 30
        assert pConfig.max_pages == 2
        assert pConfig.title == "python"
        assert pConfig.max_price == 20
        assert pConfig.min_rating == 4
        assert pRefresh is True

    def mock_initialize_database(pDatabaseFile):
        """Simule l'initialisation de la base."""

        vCalls.append("initialize_database")

    monkeypatch.setattr(main, "parse_arguments", mock_parse_arguments)

    monkeypatch.setattr(main, "process_books", mock_process_books)

    monkeypatch.setattr(main, "initialize_database", mock_initialize_database)

    main.main()

    assert vCalls == ["parse_arguments", "initialize_database", "process_books"]


def test_main_processes_jobs(monkeypatch, france_travail_available):
    """Vérifie que le mode CLI lance le traitement des offres d'emploi."""

    set_job_sources_environment(monkeypatch)

    vCalls = []

    vArguments = type(
        "Arguments",
        (),
        {
            "type": "job",
            "max_items": 100,
            "delay": 1.0,
            "timeout": 30,
            "max_pages": 2,
            "title": None,
            "max_price": None,
            "min_rating": None,
            "refresh": False,
            "keyword": "Python",
            "location": "Lille",
            "max_distance_km": 30,
            "contract": "CDI",
            "min_salary": 40000,
            "max_salary": 60000,
            "remote": True,
            "min_remote_days": 2,
            "metro_required": True,
            "max_metro_distance_km": 1.5,
            "education": "Bac+3",
            "skills": ["Python", "Django"],
            "missions": ["Développement"],
            "sources": ["france-travail", "greenhouse"],
        },
    )()

    def mock_parse_arguments():
        """Simule la lecture des arguments."""

        vCalls.append("parse_arguments")

        return vArguments

    def mock_process_jobs(pConfig):
        """Simule le traitement complet des offres d'emploi."""

        vCalls.append("process_jobs")

        assert pConfig.max_items == 100
        assert pConfig.delay == 1.0
        assert pConfig.timeout == 30
        assert pConfig.max_pages == 2

        assert pConfig.keyword == "Python"
        assert pConfig.location == "Lille"
        assert pConfig.max_distance_km == 30
        assert pConfig.contract == "CDI"
        assert pConfig.min_salary == 40000
        assert pConfig.max_salary == 60000
        assert pConfig.remote is True
        assert pConfig.min_remote_days == 2
        assert pConfig.metro_required is True
        assert pConfig.max_metro_distance_km == 1.5
        assert pConfig.education == "Bac+3"
        assert pConfig.skills == ["Python", "Django"]
        assert pConfig.missions == ["Développement"]

        assert pConfig.sources["france-travail"].enabled is True
        assert pConfig.sources["france-travail"].mode == "api"

        assert pConfig.sources["greenhouse"].enabled is True
        assert pConfig.sources["greenhouse"].mode == "api"

        assert pConfig.sources["lever"].enabled is False

    def mock_initialize_database(pDatabaseFile):
        """Simule l'initialisation de la base."""

        vCalls.append("initialize_database")

    monkeypatch.setattr(main, "parse_arguments", mock_parse_arguments)

    monkeypatch.setattr(main, "process_jobs", mock_process_jobs)

    monkeypatch.setattr(main, "initialize_database", mock_initialize_database)

    main.main()

    assert vCalls == ["parse_arguments", "initialize_database", "process_jobs"]


def test_main_without_refresh(monkeypatch):
    """Vérifie que l'option refresh est correctement transmise
    au traitement des livres.
    """

    vCalls = []

    vArguments = type(
        "Arguments",
        (),
        {
            "type": "book",
            "max_items": None,
            "delay": 0.0,
            "timeout": 10,
            "max_pages": None,
            "refresh": False,
            "title": None,
            "max_price": None,
            "min_rating": None,
        },
    )()

    def mock_parse_arguments():
        """Simule la lecture des arguments."""

        vCalls.append("parse_arguments")

        return vArguments

    def mock_process_books(pUrl, pOutputFile, pConfig, pRefresh):
        """Simule le traitement des livres."""

        vCalls.append("process_books")

        assert pConfig.max_items is None
        assert pConfig.delay == 0.0
        assert pConfig.timeout == 10
        assert pConfig.max_pages is None
        assert pRefresh is False

    def mock_initialize_database(pDatabaseFile):
        """Simule l'initialisation de la base."""

        vCalls.append("initialize_database")

    monkeypatch.setattr(main, "parse_arguments", mock_parse_arguments)

    monkeypatch.setattr(main, "process_books", mock_process_books)

    monkeypatch.setattr(main, "initialize_database", mock_initialize_database)

    main.main()

    assert vCalls == ["parse_arguments", "initialize_database", "process_books"]


def test_main_without_file(monkeypatch):
    """Vérifie que main délègue la gestion du fichier
    et du scraping à process_books().
    """

    vCalls = []

    vArguments = type(
        "Arguments",
        (),
        {
            "type": "book",
            "max_items": 100,
            "delay": 1.0,
            "timeout": 30,
            "max_pages": 2,
            "refresh": False,
            "title": None,
            "max_price": None,
            "min_rating": None,
        },
    )()

    def mock_parse_arguments():
        """Simule la lecture des arguments."""

        vCalls.append("parse_arguments")

        return vArguments

    def mock_process_books(pUrl, pOutputFile, pConfig, pRefresh):
        """Simule le traitement des livres."""

        vCalls.append("process_books")

        assert pConfig.max_items == 100
        assert pConfig.delay == 1.0
        assert pConfig.timeout == 30
        assert pConfig.max_pages == 2
        assert pRefresh is False

    def mock_initialize_database(pDatabaseFile):
        """Simule l'initialisation de la base."""

        vCalls.append("initialize_database")

    monkeypatch.setattr(main, "parse_arguments", mock_parse_arguments)

    monkeypatch.setattr(main, "process_books", mock_process_books)

    monkeypatch.setattr(main, "initialize_database", mock_initialize_database)

    main.main()

    assert vCalls == ["parse_arguments", "initialize_database", "process_books"]


# Tests de construction de configuration Jobs


def test_process_job_arguments_without_sources():
    """Vérifie qu'aucune source d'emploi n'est activée par défaut."""

    vArguments = type(
        "Arguments",
        (),
        {
            "max_items": None,
            "delay": 0.0,
            "timeout": 10,
            "max_pages": None,
            "keyword": None,
            "location": None,
            "max_distance_km": None,
            "contract": None,
            "min_salary": None,
            "max_salary": None,
            "remote": None,
            "min_remote_days": None,
            "metro_required": None,
            "max_metro_distance_km": None,
            "education": None,
            "skills": None,
            "missions": None,
            "sources": None,
        },
    )()

    vConfig = main.process_job_arguments(vArguments)

    assert all(not vSource.enabled for vSource in vConfig.sources.values())


def test_process_job_arguments_with_one_source(monkeypatch, france_travail_available):
    """Vérifie qu'une source d'emploi sélectionnée est correctement configurée."""

    set_job_sources_environment(monkeypatch)

    vArguments = type(
        "Arguments",
        (),
        {
            "max_items": 100,
            "delay": 1.0,
            "timeout": 30,
            "max_pages": 2,
            "keyword": "Python",
            "location": "Lille",
            "max_distance_km": 30,
            "contract": "CDI",
            "min_salary": 40000,
            "max_salary": 60000,
            "remote": True,
            "min_remote_days": 2,
            "metro_required": True,
            "max_metro_distance_km": 1.5,
            "education": "Bac+3",
            "skills": ["Python", "Django"],
            "missions": ["Développement"],
            "sources": ["france-travail"],
        },
    )()

    vConfig = main.process_job_arguments(vArguments)

    assert vConfig.keyword == "Python"
    assert vConfig.location == "Lille"
    assert vConfig.max_distance_km == 30
    assert vConfig.contract == "CDI"
    assert vConfig.min_salary == 40000
    assert vConfig.max_salary == 60000
    assert vConfig.remote is True
    assert vConfig.min_remote_days == 2
    assert vConfig.skills == ["Python", "Django"]

    assert vConfig.sources["france-travail"].enabled is True
    assert vConfig.sources["france-travail"].api_available is True
    assert vConfig.sources["france-travail"].mode == "api"

    assert vConfig.sources["greenhouse"].enabled is False
    assert vConfig.sources["lever"].enabled is False


def test_process_job_arguments_with_multiple_sources(
    monkeypatch, france_travail_available
):
    """Vérifie que plusieurs sources d'emploi peuvent être activées simultanément."""

    set_job_sources_environment(monkeypatch)

    vArguments = type(
        "Arguments",
        (),
        {
            "max_items": None,
            "delay": 0.0,
            "timeout": 10,
            "max_pages": None,
            "keyword": None,
            "location": None,
            "max_distance_km": None,
            "contract": None,
            "min_salary": None,
            "max_salary": None,
            "remote": None,
            "min_remote_days": None,
            "metro_required": None,
            "max_metro_distance_km": None,
            "education": None,
            "skills": None,
            "missions": None,
            "sources": ["france-travail", "greenhouse", "lever"],
        },
    )()

    vConfig = main.process_job_arguments(vArguments)

    assert vConfig.sources["france-travail"].enabled is True
    assert vConfig.sources["france-travail"].mode == "api"

    assert vConfig.sources["greenhouse"].enabled is True
    assert vConfig.sources["greenhouse"].mode == "api"

    assert vConfig.sources["lever"].enabled is True
    assert vConfig.sources["lever"].mode == "api"
