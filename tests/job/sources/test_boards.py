"""Tests des pages carrière (Lever, Ashby, Recruitee, Workable) et du filtre commun"""

from types import SimpleNamespace

import pytest

from job.csv_schema import build_job
from job.sources.ashby.parser import parse_job as parse_ashby
from job.sources.boards import (
    define_board_source,
    keep_board_jobs,
    to_country_code,
    to_dataframe,
)
from job.sources.lever.parser import parse_posting as parse_lever
from job.sources.recruitee.parser import parse_offer as parse_recruitee
from job.sources.workable.parser import parse_account as parse_workable

CONFIG = SimpleNamespace(keyword=None, location=None, max_items=None)


def test_build_job_refuses_unknown_columns():
    """Vérifie qu'une colonne mal orthographiée est signalée."""

    assert build_job(title="A")["company"] is None

    with pytest.raises(ValueError, match="titel"):
        build_job(titel="A")


@pytest.mark.parametrize(
    "pCountry, pCode",
    [("fr", "FR"), ("France", "FR"), ("Netherlands", "Netherlands"), (None, None)],
)
def test_to_country_code(pCountry, pCode):
    """Vérifie les codes pays, donnés en code ou en nom selon la plateforme."""

    assert to_country_code(pCountry) == pCode


def test_keep_board_jobs_filters_country_then_criteria():
    """Vérifie le filtre pays, mot-clé et lieu, puis la limite."""

    vJobs = to_dataframe(
        [
            build_job(title="Automaticien", location="Lille", country="FR"),
            build_job(title="Automaticien", location="Berlin", country="DE"),
            build_job(title="Automaticien télétravail", location=None, country=None),
            build_job(title="Comptable", location="Lille", country="FR"),
        ]
    )

    assert len(keep_board_jobs(vJobs, {"FR"}, "automaticien", None, None)) == 2
    assert len(keep_board_jobs(vJobs, set(), "automaticien", "Lille", None)) == 1
    assert len(keep_board_jobs(vJobs, {"FR"}, None, None, 1)) == 1


def test_board_source_scrapes_each_company(monkeypatch):
    """Vérifie la source déclarée : entreprises du .env, erreur d'une seule ignorée."""

    def fetch(pCompany):
        if pCompany == "inconnue":
            raise ValueError("404")
        return to_dataframe([build_job(title=f"Poste {pCompany}", country="FR")])

    vSource = define_board_source("essai", "Essai", "ESSAI_COMPANIES", "", fetch)

    assert vSource.get_unavailability_reason() == "non configurée"

    monkeypatch.setenv("ESSAI_COMPANIES", "acme, inconnue,globex")
    vJobs = vSource.scrape(vSource.load_parameters(CONFIG), CONFIG)

    assert list(vJobs["title"]) == ["Poste acme", "Poste globex"]
    assert vSource.category == "company"


def test_lever_posting():
    """Vérifie la lecture d'une offre Lever."""

    vJob = parse_lever(
        {
            "id": "744a",
            "text": "Account Executive",
            "categories": {"location": "Paris", "commitment": "Full-time"},
            "country": "FR",
            "workplaceType": "hybrid",
            "createdAt": 1791900863876,
            "descriptionPlain": "Mission",
            "additionalPlain": "Avantages",
            "hostedUrl": "https://jobs.lever.co/qonto/744a",
        },
        "qonto",
    )

    assert vJob["company"] == "Qonto"
    assert vJob["country"] == "FR"
    assert vJob["remote_type"] == "hybrid"
    assert vJob["description"] == "Mission\n\nAvantages"
    assert vJob["published_at"].startswith("2026-")


def test_ashby_job():
    """Vérifie la lecture d'une offre Ashby, pays donné en nom anglais."""

    vJob = parse_ashby(
        {
            "id": "40f9",
            "title": "Data Engineer",
            "employmentType": "FullTime",
            "location": "Paris",
            "address": {"postalAddress": {"addressCountry": "France"}},
            "isRemote": False,
            "publishedAt": "2026-09-09T13:17:05.420+00:00",
            "jobUrl": "https://jobs.ashbyhq.com/alan/40f9",
            "descriptionPlain": "Données",
        },
        "alan",
    )

    assert vJob["country"] == "FR"
    assert vJob["contract_type"] == "Temps plein"
    assert vJob["remote"] is None


def test_recruitee_offer():
    """Vérifie la lecture d'une offre Recruitee, salaire compris."""

    vJob = parse_recruitee(
        {
            "id": 2783543,
            "title": "Head of Product",
            "company_name": "bunq",
            "location": "Amsterdam, Netherlands",
            "country_code": "NL",
            "description": "<p>Produit</p>",
            "requirements": "<p>Expérience</p>",
            "salary": {"min": 5000, "max": 6000, "currency": "EUR"},
            "careers_url": "https://careers.bunq.com/o/head-of-product",
        },
        "bunq",
    )

    assert vJob["source_id"] == "2783543"
    assert vJob["description"] == "Produit\n\nExpérience"
    assert vJob["salary_min"] == 5000


def test_workable_account():
    """Vérifie la lecture d'un compte Workable et de son nom d'entreprise."""

    vJobs = parse_workable(
        {
            "name": "Hugging Face",
            "jobs": [
                {
                    "title": "ML Engineer",
                    "shortcode": "81B4",
                    "country": "France",
                    "city": "Paris",
                    "telecommuting": True,
                    "description": "<p>Open source</p>",
                    "url": "https://apply.workable.com/j/81B4",
                }
            ],
        },
        "huggingface",
    )

    assert vJobs.iloc[0]["company"] == "Hugging Face"
    assert vJobs.iloc[0]["location"] == "Paris, France"
    assert vJobs.iloc[0]["country"] == "FR"
    assert vJobs.iloc[0]["remote"]
