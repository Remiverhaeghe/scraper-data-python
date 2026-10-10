"""Tests de la transformation des offres Hacker News"""

import pytest

from job.csv_schema import JOB_COLUMNS
from job.sources.hackernews.parser import parse_job, parse_jobs


def build_comment(**pValues):
    """Construit un commentaire proche d'une réponse réelle."""

    rComment = {
        "id": 49922609,
        "created_at": "2026-10-01T15:03:36.000Z",
        "text": (
            "Sidekick Labs | Senior SWE | REMOTE (US Timezones) | Full-time"
            " | $170k to $230k<p>Sidekick builds <i>AI</i> security software.</p>"
        ),
    }

    rComment.update(pValues)

    return rComment


def test_parse_job():
    """Vérifie l'extraction de l'en-tête et du contenu d'une offre."""

    rJob = parse_job(build_comment())

    assert rJob["source"] == "hackernews"
    assert rJob["source_id"] == "49922609"
    assert rJob["url"] == "https://news.ycombinator.com/item?id=49922609"
    assert rJob["company"] == "Sidekick Labs"
    assert rJob["title"] == "Senior SWE"
    assert rJob["location"] == "REMOTE (US Timezones)"
    assert rJob["contract_type"] == "Full-time"
    assert rJob["salary_label"] == "$170k to $230k"
    assert rJob["remote"] is True
    assert rJob["description"] == "Sidekick builds AI security software."
    assert rJob["published_at"] == "2026-10-01T15:03:36.000Z"


def test_parse_job_with_dash_separator_and_onsite():
    """Vérifie un en-tête séparé par des tirets, sans télétravail."""

    rJob = parse_job(
        build_comment(text="Acme (Paris) – Backend Engineer – ONSITE<p>Python</p>")
    )

    assert rJob["company"] == "Acme (Paris)"
    assert rJob["title"] == "Backend Engineer"
    assert rJob["location"] == "ONSITE"
    assert rJob["remote"] is None


@pytest.mark.parametrize(
    "pHeader, pCompany",
    [
        ("Snout https://snout.com/", "Snout"),
        ("Smarkets ( https://www.smarkets.com )", "Smarkets"),
        ("Acme (Series B)", "Acme (Series B)"),
    ],
)
def test_parse_job_removes_company_url(pHeader, pCompany):
    """Vérifie que le lien du site est retiré du nom de l'entreprise."""

    rJob = parse_job(build_comment(text=f"{pHeader} | Engineer<p>Python</p>"))

    assert rJob["company"] == pCompany


@pytest.mark.parametrize(
    "pHeader, pExpected",
    [
        (
            "Propel Labs | Staff Engineer, Quality | Remote (US hours) | Full-time"
            " | https://propellabs.ai",
            ("Staff Engineer, Quality", "Remote (US hours)", "Full-time", None),
        ),
        (
            "Acme | Contract Manager | Paris, France | Contract or Full-time"
            " | Visa sponsorship | acme.io/jobs",
            ("Contract Manager", "Paris, France", "Contract or Full-time", None),
        ),
        (
            "Acme | Data Engineer | London | Hybrid | €70k - €90k",
            ("Data Engineer", "London | Hybrid", None, "€70k - €90k"),
        ),
        ("Acme", ("Acme", None, None, None)),
        (
            "Smarkets ( https://www.smarkets.com ) | Full Time | Hybrid (London)",
            (None, "Hybrid (London)", "Full Time", None),
        ),
        (
            "Fastly | Software Engineers | ONSITE | Full-time When you look at the"
            " headers of major websites, you will see us everywhere on the web",
            ("Software Engineers", "ONSITE", None, None),
        ),
    ],
)
def test_parse_job_classifies_header_segments(pHeader, pExpected):
    """Vérifie la répartition des segments entre poste, lieu, contrat et salaire."""

    rJob = parse_job(build_comment(text=f"{pHeader}<p>Python</p>"))

    assert (
        rJob["title"],
        rJob["location"],
        rJob["contract_type"],
        rJob["salary_label"],
    ) == pExpected


def test_parse_jobs_ignores_deleted_comments():
    """Vérifie que les commentaires supprimés sont ignorés."""

    rJobs = parse_jobs([build_comment(), {"id": 2, "text": None}])

    assert list(rJobs.columns) == JOB_COLUMNS
    assert rJobs["source_id"].tolist() == ["49922609"]
