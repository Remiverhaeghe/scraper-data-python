"""Tests du service Himalayas"""

from job.sources.himalayas import service
from job.sources.himalayas.service import scrape_jobs


def mock_search(pPageSizes, pTotalCount, pCalls):
    """Simule search_jobs avec un nombre d'offres prévu par page."""

    def search(pQuery, pCountry, pPage):
        pCalls.append({"query": pQuery, "country": pCountry, "page": pPage})

        vCount = pPageSizes[pPage - 1] if pPage <= len(pPageSizes) else 0

        rData = {
            "jobs": [{"guid": f"{pPage}-{vIndex}"} for vIndex in range(vCount)],
            "totalCount": pTotalCount,
        }

        return rData

    return search


def test_scrape_jobs_stops_when_total_is_reached(monkeypatch):
    """Vérifie l'arrêt lorsque toutes les offres ont été récupérées."""

    vCalls = []

    monkeypatch.setattr(service, "search_jobs", mock_search([20, 5], 25, vCalls))

    rJobs = scrape_jobs("python")

    assert len(rJobs) == 25
    assert [vCall["page"] for vCall in vCalls] == [1, 2]
    assert vCalls[0]["country"] == "France"


def test_scrape_jobs_applies_default_page_limit(monkeypatch):
    """Vérifie le plafond de pages appliqué par défaut."""

    vCalls = []

    monkeypatch.setattr(service, "search_jobs", mock_search([20] * 10, 688, vCalls))

    rJobs = scrape_jobs("python")

    assert len(vCalls) == service.DEFAULT_MAX_PAGES
    assert len(rJobs) == 20 * service.DEFAULT_MAX_PAGES


def test_scrape_jobs_applies_max_items(monkeypatch):
    """Vérifie l'arrêt et la limitation au nombre d'offres demandé."""

    vCalls = []

    monkeypatch.setattr(service, "search_jobs", mock_search([20] * 10, 688, vCalls))

    rJobs = scrape_jobs("python", pMaxItems=30)

    assert len(rJobs) == 30
    assert len(vCalls) == 2


def test_scrape_jobs_without_result(monkeypatch):
    """Vérifie le résultat d'une recherche sans offre."""

    monkeypatch.setattr(service, "search_jobs", mock_search([], 0, []))

    assert scrape_jobs("cobol").empty
