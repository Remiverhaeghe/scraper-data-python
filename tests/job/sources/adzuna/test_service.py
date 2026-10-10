"""Tests du service Adzuna"""

from job.sources.adzuna import service
from job.sources.adzuna.service import scrape_jobs


def mock_search(pPages, pCalls):
    """Simule search_jobs en renvoyant le nombre d'offres prévu par page."""

    def search(pConfig, pParams, pPage, pResultsPerPage):
        pCalls.append({"page": pPage, "results_per_page": pResultsPerPage})

        vCount = pPages[pPage - 1] if pPage <= len(pPages) else 0

        rData = {"results": [{"id": f"{pPage}-{vIndex}"} for vIndex in range(vCount)]}

        return rData

    return search


def test_scrape_jobs_stops_on_last_page(monkeypatch):
    """Vérifie l'arrêt lorsqu'une page n'est pas complète."""

    vCalls = []

    monkeypatch.setattr(service, "search_jobs", mock_search([50, 10], vCalls))

    rJobs = scrape_jobs(None, {})

    assert len(rJobs) == 60
    assert [vCall["page"] for vCall in vCalls] == [1, 2]


def test_scrape_jobs_applies_default_page_limit(monkeypatch):
    """Vérifie le plafond de pages appliqué pour préserver le quota."""

    vCalls = []

    monkeypatch.setattr(service, "search_jobs", mock_search([50] * 10, vCalls))

    rJobs = scrape_jobs(None, {})

    assert len(vCalls) == service.DEFAULT_MAX_PAGES
    assert len(rJobs) == 50 * service.DEFAULT_MAX_PAGES


def test_scrape_jobs_respects_max_pages(monkeypatch):
    """Vérifie que max_pages remplace le plafond par défaut."""

    vCalls = []

    monkeypatch.setattr(service, "search_jobs", mock_search([50] * 10, vCalls))

    scrape_jobs(None, {}, pMaxPages=2)

    assert len(vCalls) == 2


def test_scrape_jobs_keeps_page_size_constant_with_max_items(monkeypatch):
    """Vérifie que la taille de page reste fixe pour ne pas décaler les résultats."""

    vCalls = []

    monkeypatch.setattr(service, "search_jobs", mock_search([50] * 10, vCalls))

    rJobs = scrape_jobs(None, {}, pMaxItems=70)

    assert len(rJobs) == 70
    assert {vCall["results_per_page"] for vCall in vCalls} == {50}
