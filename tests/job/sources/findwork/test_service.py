"""Tests du service Findwork"""

import pytest

from job.sources.findwork import service
from job.sources.findwork.config import load_config
from job.sources.findwork.service import scrape_jobs


def mock_get_jobs(pPageSizes, pCalls):
    """Simule get_jobs avec un nombre d'offres prévu par page."""

    def get_jobs(pConfig, pParams, pPage):
        pCalls.append(pPage)

        vCount = pPageSizes[pPage - 1]

        rData = {
            "results": [
                {"id": f"{pPage}-{vIndex}", "role": "Développeur Python"}
                for vIndex in range(vCount)
            ],
            "next": "page suivante" if pPage < len(pPageSizes) else None,
        }

        return rData

    return get_jobs


def test_scrape_jobs_follows_next_page(monkeypatch):
    """Vérifie le suivi de la pagination jusqu'à la dernière page."""

    vCalls = []

    monkeypatch.setattr(service, "get_jobs", mock_get_jobs([50, 10], vCalls))

    rJobs = scrape_jobs(None, {"search": "python"})

    assert len(rJobs) == 60
    assert vCalls == [1, 2]


def test_scrape_jobs_applies_default_page_limit(monkeypatch):
    """Vérifie le plafond de pages appliqué par défaut."""

    vCalls = []

    monkeypatch.setattr(service, "get_jobs", mock_get_jobs([50] * 10, vCalls))

    scrape_jobs(None, {})

    assert len(vCalls) == service.DEFAULT_MAX_PAGES


def test_scrape_jobs_applies_max_items(monkeypatch):
    """Vérifie l'arrêt et la limitation au nombre d'offres demandé."""

    vCalls = []

    monkeypatch.setattr(service, "get_jobs", mock_get_jobs([50] * 10, vCalls))

    rJobs = scrape_jobs(None, {}, pMaxItems=70)

    assert len(rJobs) == 70
    assert vCalls == [1, 2]


def test_load_config_requires_key(monkeypatch):
    """Vérifie que l'erreur nomme la variable manquante."""

    monkeypatch.delenv("FINDWORK_API_KEY", raising=False)

    with pytest.raises(ValueError, match="FINDWORK_API_KEY"):
        load_config()
