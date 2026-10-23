"""Test d'intégration : recherche réelle, base, statistiques, web et export

Seul le réseau est simulé. Clients, parsers, services, agrégation, base SQLite,
historique, tableau de bord web et export s'exécutent comme en production.
"""

import pandas as pd
import pytest
import requests
from fastapi.testclient import TestClient

from gui.job_controller import JobController
from job.export import export_offers
from job.statistics import load_statistics
from storage.database import initialize_database
from storage.history_repository import get_history
from storage.job_offers import get_offers
from tests.job.sources.adzuna.test_parser import build_job as build_adzuna_job
from tests.job.sources.arbeitnow.test_parser import build_job as build_arbeitnow_job
from tests.job.sources.fake_http import FakeJsonResponse
from tests.job.sources.findwork.test_parser import build_job as build_findwork_job
from tests.job.sources.himalayas.test_parser import build_job as build_himalayas_job
from tests.job.sources.jobicy.test_parser import build_job as build_jobicy_job
from tests.job.sources.jooble.test_parser import build_job as build_jooble_job
from tests.job.sources.remotive.test_parser import build_job as build_remotive_job
from web.app import app, get_database_file

SOURCES = [
    "remotive",
    "arbeitnow",
    "jobicy",
    "himalayas",
    "jooble",
    "findwork",
    "adzuna",
]

# Clés factices des sources qui en exigent une
API_KEYS = {
    "JOOBLE_API_KEY": "cle-jooble",
    "FINDWORK_API_KEY": "cle-findwork",
    "ADZUNA_APP_ID": "identifiant-adzuna",
    "ADZUNA_APP_KEY": "cle-adzuna",
}

# Réponse de chaque API, identifiée par son nom de domaine
API_RESPONSES = {
    "remotive.com": {"jobs": [build_remotive_job()]},
    "arbeitnow.com": {"data": [build_arbeitnow_job()], "links": {"next": None}},
    "jobicy.com": {"jobs": [build_jobicy_job()]},
    "himalayas.app": {"jobs": [build_himalayas_job()], "totalCount": 1},
    "jooble.org": {"jobs": [build_jooble_job()], "totalCount": 1},
    "findwork.dev": {"results": [build_findwork_job()], "next": None},
    "api.adzuna.com": {"results": [build_adzuna_job()], "count": 1},
}


class FakeResponse(FakeJsonResponse):
    """Réponse simulée d'une API, en succès ou en erreur."""

    def __init__(self, pData, pStatusCode=200):
        self.data = pData
        self.status_code = pStatusCode

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code}", response=self)

    def json(self):
        return self.data


def simulate_apis(pMonkeypatch, pFailingHost=None):
    """Répond aux appels des sources ; pFailingHost renvoie une erreur 500."""

    def mock_request(pMethod, pUrl, **pOptions):
        vHost = next(vHost for vHost in API_RESPONSES if vHost in pUrl)

        if vHost == pFailingHost:
            rResponse = FakeResponse({}, 500)
        else:
            rResponse = FakeResponse(API_RESPONSES[vHost])

        return rResponse

    pMonkeypatch.setattr(requests, "request", mock_request)
    pMonkeypatch.setattr("utils.api_client.validate_url", lambda pUrl: True)

    for vName, vValue in API_KEYS.items():
        pMonkeypatch.setenv(vName, vValue)


@pytest.fixture
def database_file(tmp_path, monkeypatch):
    """Crée une base vide, utilisée par le traitement et par le web."""

    rDatabaseFile = tmp_path / "scraper.db"

    initialize_database(rDatabaseFile)

    monkeypatch.setattr("job.application.DATABASE_FILE", rDatabaseFile)

    app.dependency_overrides[get_database_file] = lambda: rDatabaseFile

    yield rDatabaseFile

    app.dependency_overrides.clear()


def test_search_feeds_database_dashboard_and_export(
    database_file, monkeypatch, tmp_path, web_login
):
    """Vérifie le parcours complet d'une recherche jusqu'à l'export."""

    simulate_apis(monkeypatch)

    vResult = JobController().search_jobs(SOURCES, {"max_items": 50})

    assert vResult.status == "success"
    assert sorted(vResult.items["source"]) == sorted(SOURCES)
    assert vResult.items["is_new"].all()

    vStatistics = load_statistics(database_file)

    assert vStatistics["offers"] == len(SOURCES)
    assert vStatistics["new_offers"] == len(SOURCES)
    assert sorted(get_history(database_file)[0].parameters["sources"]) == sorted(
        SOURCES
    )

    with TestClient(app) as vClient:
        web_login(vClient)

        vDashboard = vClient.get("/")
        vOffers = vClient.get("/offers")

        vOffer = get_offers(database_file).iloc[0]

        vApplication = vClient.post(
            "/offer/application",
            data={
                "source": vOffer["source"],
                "id": vOffer["source_id"],
                "status": "APPLIED",
            },
        )

    assert vDashboard.status_code == 200
    assert "Offres actives en base" in vDashboard.text
    assert f"{len(SOURCES)} offres" in vOffers.text
    assert vApplication.status_code == 200
    assert load_statistics(database_file)["applications"] == 1

    vExportFile = tmp_path / "offres.csv"

    assert export_offers(get_offers(database_file), vExportFile) == len(SOURCES)
    assert len(pd.read_csv(vExportFile, sep=";", encoding="utf-8-sig")) == len(SOURCES)

    vSecondResult = JobController().search_jobs(SOURCES, {"max_items": 50})

    assert not vSecondResult.items["is_new"].any()
    assert load_statistics(database_file)["offers"] == len(SOURCES)


def test_failing_source_does_not_block_the_others(database_file, monkeypatch):
    """Vérifie qu'une source en panne laisse les autres enregistrer leurs offres."""

    simulate_apis(monkeypatch, pFailingHost="jobicy.com")

    vResult = JobController().search_jobs(SOURCES, {"max_items": 50})

    assert vResult.status == "partial"
    assert "Jobicy" in vResult.error_message
    assert "jobicy" not in set(vResult.items["source"])
    assert len(vResult.items) == len(SOURCES) - 1
    assert get_history(database_file)[0].status == "partial"
