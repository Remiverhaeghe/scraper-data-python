"""Tests du service Hacker News"""

from job.sources.hackernews import service
from job.sources.hackernews.service import scrape_jobs


def build_thread():
    """Construit un fil contenant plusieurs offres."""

    rThread = {
        "children": [
            {"id": 1, "text": "Acme | Python Engineer | Paris<p>Django</p>"},
            {"id": 2, "text": "Beta | Java Engineer | Berlin<p>Spring</p>"},
            {"id": 3, "text": "Gamma | Python Developer | REMOTE<p>FastAPI</p>"},
            {"id": 4, "text": None},
        ]
    }

    return rThread


def mock_thread(monkeypatch):
    """Remplace les appels réseau par un fil prédéfini."""

    monkeypatch.setattr(service, "find_latest_thread_id", lambda: "100")
    monkeypatch.setattr(service, "get_thread", lambda pThreadId: build_thread())


def test_scrape_jobs_filters_keyword(monkeypatch):
    """Vérifie le filtrage local sur le mot-clé."""

    mock_thread(monkeypatch)

    rJobs = scrape_jobs("python")

    assert rJobs["source_id"].tolist() == ["1", "3"]


def test_scrape_jobs_filters_location_before_limit(monkeypatch):
    """Vérifie que le filtrage est appliqué avant la limite."""

    mock_thread(monkeypatch)

    rJobs = scrape_jobs("engineer", "berlin", pMaxItems=1)

    assert rJobs["source_id"].tolist() == ["2"]


def test_scrape_jobs_without_result(monkeypatch):
    """Vérifie le résultat lorsqu'aucune offre ne correspond."""

    mock_thread(monkeypatch)

    assert scrape_jobs("cobol").empty
