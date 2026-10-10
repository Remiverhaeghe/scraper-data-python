"""Tests du service Jooble"""

import pytest

from job.sources.jooble import service
from job.sources.jooble.config import load_config
from job.sources.jooble.service import build_body, scrape_jobs


def mock_search(pPageSizes, pTotalCount, pCalls):
    """Simule search_jobs avec un nombre d'offres prévu par page."""

    def search(pConfig, pBody):
        pCalls.append(pBody)

        vPage = int(pBody["page"])
        vCount = pPageSizes[vPage - 1] if vPage <= len(pPageSizes) else 0

        rData = {
            "totalCount": pTotalCount,
            "jobs": [{"id": f"{vPage}-{vIndex}"} for vIndex in range(vCount)],
        }

        return rData

    return search


def test_build_body_defaults_to_france():
    """Vérifie le corps de requête sans ville ni rayon."""

    assert build_body({"keywords": "python"}, 2, 20) == {
        "keywords": "python",
        "location": "France",
        "page": "2",
        "ResultOnPage": "20",
    }


def test_build_body_with_radius():
    """Vérifie la transmission de la ville et du rayon."""

    vBody = build_body({"keywords": "", "location": "Lille", "radius": 30}, 1, 20)

    assert vBody["location"] == "Lille"
    assert vBody["radius"] == "30"


def test_scrape_jobs_stops_on_last_page(monkeypatch):
    """Vérifie l'arrêt lorsqu'une page n'est pas complète."""

    vCalls = []

    monkeypatch.setattr(service, "search_jobs", mock_search([20, 5], 25, vCalls))

    rJobs = scrape_jobs(None, {"keywords": "python"})

    assert len(rJobs) == 25
    assert [vCall["page"] for vCall in vCalls] == ["1", "2"]


def test_scrape_jobs_applies_default_page_limit(monkeypatch):
    """Vérifie le plafond de pages appliqué par défaut."""

    vCalls = []

    monkeypatch.setattr(service, "search_jobs", mock_search([20] * 10, 500, vCalls))

    scrape_jobs(None, {})

    assert len(vCalls) == service.DEFAULT_MAX_PAGES


def test_scrape_jobs_keeps_page_size_constant(monkeypatch):
    """Vérifie que la taille de page reste fixe avec max_items."""

    vCalls = []

    monkeypatch.setattr(service, "search_jobs", mock_search([20] * 10, 500, vCalls))

    rJobs = scrape_jobs(None, {}, pMaxItems=30)

    assert len(rJobs) == 30
    assert {vCall["ResultOnPage"] for vCall in vCalls} == {"20"}


def test_load_config_requires_key(monkeypatch):
    """Vérifie que l'erreur nomme la variable manquante."""

    monkeypatch.delenv("JOOBLE_API_KEY", raising=False)

    with pytest.raises(ValueError, match="JOOBLE_API_KEY"):
        load_config()
