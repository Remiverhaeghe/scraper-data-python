"""Tests des entreprises suivies sur les pages carrière"""

import importlib

import pytest
import requests

import job.company_pages as company_pages
from job.company_pages import add_company_from_url, load_company_list, read_career_url
from storage.database import initialize_database


@pytest.mark.parametrize(
    ("pUrl", "pExpected"),
    [
        ("https://jobs.lever.co/qonto/abc", ("lever", "qonto")),
        ("https://jobs.smartrecruiters.com/Kiabi", ("smartrecruiters", "Kiabi")),
        ("https://jobs.ashbyhq.com/alan", ("ashby", "alan")),
        ("https://boards.greenhouse.io/doctolib", ("greenhouse", "doctolib")),
        ("https://acme.recruitee.com/o/dev", ("recruitee", "acme")),
        ("https://apply.workable.com/exotec/j/1", ("workable", "exotec")),
        (
            "https://valeo.wd3.myworkdayjobs.com/fr-FR/valeo_jobs/job/x",
            ("workday", "Valeo=valeo.wd3/valeo/valeo_jobs"),
        ),
        (
            "https://ag.wd3.myworkdayjobs.com/Airbus",
            ("workday", "Airbus=ag.wd3/ag/Airbus"),
        ),
    ],
)
def test_career_url_gives_platform_and_identifier(pUrl, pExpected):
    """Vérifie la plateforme et l'identifiant lus dans l'adresse d'un site carrière."""

    assert read_career_url(pUrl) == pExpected


def test_unknown_or_missing_company_is_refused(tmp_path, monkeypatch):
    """Vérifie le refus d'une adresse inconnue, d'une entreprise absente, et le doublon."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    monkeypatch.delenv("ASHBY_COMPANIES", raising=False)

    with pytest.raises(ValueError, match="Adresse non reconnue"):
        read_career_url("https://www.exemple.fr/jobs")

    def missing(_pPlatform, _pCompany):
        raise requests.HTTPError("404")

    monkeypatch.setattr(company_pages, "count_published_offers", missing)

    with pytest.raises(ValueError, match="ne connaît pas"):
        add_company_from_url(vDatabaseFile, "https://jobs.ashbyhq.com/inconnue")

    monkeypatch.setattr(company_pages, "count_published_offers", lambda *pArgs: 3)

    assert "déjà suivie" in add_company_from_url(
        vDatabaseFile, "https://jobs.ashbyhq.com/alan"
    )
    assert "alan" in load_company_list("ashby", vDatabaseFile)


# Workday attend un site au format [Nom=]hôte/tenant/site.
ACME = {vPlatform: "acme" for vPlatform in company_pages.PLATFORMS}
ACME["workday"] = "Acme=acme.wd3/acme/jobs"


@pytest.mark.parametrize(
    ("pPlatform", "pFunction", "pAnswer"),
    [
        ("smartrecruiters", "get_postings", {"totalFound": 4}),
        ("lever", "get_postings", [{}, {}, {}, {}]),
        ("ashby", "get_jobs", [{}, {}, {}, {}]),
        ("greenhouse", "get_jobs", {"jobs": [{}, {}, {}, {}]}),
        ("recruitee", "get_offers", [{}, {}, {}, {}]),
        ("workable", "get_account", {"jobs": [{}, {}, {}, {}]}),
        ("workday", "search_jobs", {"total": 4}),
    ],
)
def test_published_offers_are_counted_on_each_platform(
    pPlatform, pFunction, pAnswer, monkeypatch
):
    """Vérifie le nombre d'offres lu dans la réponse propre à chaque plateforme."""

    vClient = importlib.import_module(f"job.sources.{pPlatform}.client")
    monkeypatch.setattr(vClient, pFunction, lambda *pArgs: pAnswer)

    assert company_pages.count_published_offers(pPlatform, ACME[pPlatform]) == 4


def test_empty_answers_count_no_offer(monkeypatch):
    """Vérifie qu'une réponse sans total ni liste compte zéro offre."""

    vSmartRecruiters = importlib.import_module("job.sources.smartrecruiters.client")
    vWorkday = importlib.import_module("job.sources.workday.client")
    monkeypatch.setattr(vSmartRecruiters, "get_postings", lambda *pArgs: {})
    monkeypatch.setattr(vWorkday, "search_jobs", lambda *pArgs: {})

    assert company_pages.count_published_offers("smartrecruiters", "acme") == 0
    assert company_pages.count_published_offers("workday", ACME["workday"]) == 0
