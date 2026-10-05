# ============================================================================
# Tests du service de scraping Lever
# ============================================================================

import pandas as pd

from job.sources.lever.service import scrape_jobs


def test_scrape_jobs(monkeypatch):
    """
    Vérifie le scraping de plusieurs pages Lever.
    """

    vJobsPage1 = [
        {
            "id": "job-1",
            "text": "Python Developer"
        },
        {
            "id": "job-2",
            "text": "Java Developer"
        }
    ]

    vJobsPage2 = [
        {
            "id": "job-3",
            "text": "DevOps Engineer"
        }
    ]

    vCalls = []

    def mock_get_jobs(
        pSite,
        pLimit=100,
        pSkip=0
    ):
        vCalls.append(
            {
                "site": pSite,
                "limit": pLimit,
                "skip": pSkip
            }
        )

        if pSkip == 0:
            rJobs = vJobsPage1
        else:
            rJobs = vJobsPage2

        return rJobs

    monkeypatch.setattr(
        "job.sources.lever.service.get_jobs",
        mock_get_jobs
    )

    rData = scrape_jobs(
        "example-company",
        pLimit=2
    )

    assert isinstance(rData, pd.DataFrame)
    assert len(rData) == 3

    assert list(rData["source"]) == [
        "lever",
        "lever",
        "lever"
    ]

    assert vCalls == [
        {
            "site": "example-company",
            "limit": 2,
            "skip": 0
        },
        {
            "site": "example-company",
            "limit": 2,
            "skip": 2
        }
    ]


def test_scrape_jobs_without_results(monkeypatch):
    """
    Vérifie le comportement lorsqu'aucune offre n'est disponible.
    """

    def mock_get_jobs(
        pSite,
        pLimit=100,
        pSkip=0
    ):
        return []

    monkeypatch.setattr(
        "job.sources.lever.service.get_jobs",
        mock_get_jobs
    )

    rData = scrape_jobs(
        "example-company"
    )

    assert isinstance(rData, pd.DataFrame)
    assert rData.empty


def test_scrape_jobs_single_page(monkeypatch):
    """
    Vérifie qu'une seule page est demandée lorsque le nombre
    d'offres est inférieur à la limite.
    """

    vJobs = [
        {
            "id": "job-1",
            "text": "Python Developer"
        }
    ]

    vCalls = []

    def mock_get_jobs(
        pSite,
        pLimit=100,
        pSkip=0
    ):
        vCalls.append(pSkip)
        return vJobs

    monkeypatch.setattr(
        "job.sources.lever.service.get_jobs",
        mock_get_jobs
    )

    rData = scrape_jobs(
        "example-company",
        pLimit=100
    )

    assert len(rData) == 1
    assert vCalls == [0]


# ============================================================================
# Tests de la limitation du nombre d'offres Lever
# ============================================================================

def test_scrape_jobs_respects_max_items(monkeypatch):
    """
    Vérifie que le service Lever respecte le nombre maximum d'offres demandé.
    """

    # Vérifie que le dernier appel utilise uniquement les offres restantes.
    vCalls = []

    def mock_get_jobs(
        pSite,
        pLimit=100,
        pSkip=0
    ):
        vCalls.append(
            {
                "site": pSite,
                "limit": pLimit,
                "skip": pSkip
            }
        )

        vJobs = []

        for vIndex in range(pLimit):
            vJobs.append(
                {
                    "id": f"job-{pSkip + vIndex + 1}",
                    "text": f"Offre {pSkip + vIndex + 1}"
                }
            )

        rJobs = vJobs

        return rJobs

    monkeypatch.setattr(
        "job.sources.lever.service.get_jobs",
        mock_get_jobs
    )

    rResult = scrape_jobs(
        "test-site",
        pLimit=100,
        pMaxItems=150
    )

    assert len(rResult) == 150

    assert vCalls == [
        {
            "site": "test-site",
            "limit": 100,
            "skip": 0
        },
        {
            "site": "test-site",
            "limit": 50,
            "skip": 100
        }
    ]


def test_scrape_jobs_does_not_limit_when_max_items_is_none(
    monkeypatch
):
    """
    Vérifie que le comportement historique est conservé sans limite globale.
    """

    # Vérifie que la pagination existante continue de fonctionner sans limite.
    vCalls = []

    def mock_get_jobs(
        pSite,
        pLimit=100,
        pSkip=0
    ):
        vCalls.append(
            {
                "site": pSite,
                "limit": pLimit,
                "skip": pSkip
            }
        )

        if pSkip == 0:
            rJobs = [
                {
                    "id": "job-1",
                    "text": "Offre 1"
                },
                {
                    "id": "job-2",
                    "text": "Offre 2"
                }
            ]
        else:
            rJobs = []

        return rJobs

    monkeypatch.setattr(
        "job.sources.lever.service.get_jobs",
        mock_get_jobs
    )

    rResult = scrape_jobs(
        "test-site",
        pLimit=2,
        pMaxItems=None
    )

    assert len(rResult) == 2

    assert vCalls == [
        {
            "site": "test-site",
            "limit": 2,
            "skip": 0
        },
        {
            "site": "test-site",
            "limit": 2,
            "skip": 2
        }
    ]


def test_scrape_jobs_max_items_smaller_than_page_size(
    monkeypatch
):
    """
    Vérifie qu'une seule requête est adaptée lorsque max_items
    est inférieur à la taille d'une page.
    """

    # Vérifie que l'API reçoit directement la limite réellement nécessaire.
    vCalls = []

    def mock_get_jobs(
        pSite,
        pLimit=100,
        pSkip=0
    ):
        vCalls.append(
            {
                "site": pSite,
                "limit": pLimit,
                "skip": pSkip
            }
        )

        vJobs = []

        for vIndex in range(pLimit):
            vJobs.append(
                {
                    "id": f"job-{vIndex + 1}",
                    "text": f"Offre {vIndex + 1}"
                }
            )

        rJobs = vJobs

        return rJobs

    monkeypatch.setattr(
        "job.sources.lever.service.get_jobs",
        mock_get_jobs
    )

    rResult = scrape_jobs(
        "test-site",
        pLimit=100,
        pMaxItems=25
    )

    assert len(rResult) == 25

    assert vCalls == [
        {
            "site": "test-site",
            "limit": 25,
            "skip": 0
        }
    ]