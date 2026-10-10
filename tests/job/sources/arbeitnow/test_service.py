"""Tests du service Arbeitnow"""

from job.sources.arbeitnow import service
from job.sources.arbeitnow.service import scrape_jobs


def build_page(pJobs, pHasNext):
    """Construit une page de réponse Arbeitnow."""

    rPage = {
        "data": [
            {"slug": vSlug, "title": vTitle, "location": vLocation}
            for vSlug, vTitle, vLocation in pJobs
        ],
        "links": {"next": "https://www.arbeitnow.com/api?page=2" if pHasNext else None},
    }

    return rPage


def mock_get_jobs(pPages, pCalls):
    """Simule get_jobs à partir de pages prédéfinies."""

    def get_jobs(pPage):
        pCalls.append(pPage)

        rPage = pPages[pPage - 1]

        return rPage

    return get_jobs


def test_scrape_jobs_filters_before_limit(monkeypatch):
    """Vérifie que le filtrage local est appliqué avant la limite."""

    vCalls = []

    vPages = [
        build_page(
            [
                ("1", "Marketing Manager", "Berlin"),
                ("2", "Python Developer", "Berlin"),
                ("3", "Python Engineer", "Paris"),
            ],
            pHasNext=True,
        ),
        build_page([("4", "Senior Python Developer", "Lyon")], pHasNext=False),
    ]

    monkeypatch.setattr(service, "get_jobs", mock_get_jobs(vPages, vCalls))

    rJobs = scrape_jobs("python", pMaxItems=3)

    assert rJobs["source_id"].tolist() == ["2", "3", "4"]
    assert vCalls == [1, 2]


def test_scrape_jobs_filters_location(monkeypatch):
    """Vérifie le filtrage local sur la localisation."""

    vPages = [
        build_page(
            [("1", "Python Developer", "Berlin"), ("2", "Python Engineer", "Paris")],
            pHasNext=False,
        )
    ]

    monkeypatch.setattr(service, "get_jobs", mock_get_jobs(vPages, []))

    rJobs = scrape_jobs("python", "paris")

    assert rJobs["source_id"].tolist() == ["2"]


def test_scrape_jobs_applies_default_page_limit(monkeypatch):
    """Vérifie le plafond de pages appliqué par défaut."""

    vCalls = []

    vPages = [build_page([("1", "Python", "Berlin")], pHasNext=True)] * 5

    monkeypatch.setattr(service, "get_jobs", mock_get_jobs(vPages, vCalls))

    scrape_jobs("python")

    assert len(vCalls) == service.DEFAULT_MAX_PAGES


def test_scrape_jobs_without_result(monkeypatch):
    """Vérifie le résultat lorsqu'aucune offre ne correspond."""

    vPages = [build_page([("1", "Marketing", "Berlin")], pHasNext=False)]

    monkeypatch.setattr(service, "get_jobs", mock_get_jobs(vPages, []))

    rJobs = scrape_jobs("python")

    assert rJobs.empty
