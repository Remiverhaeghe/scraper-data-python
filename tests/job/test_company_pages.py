"""Tests des entreprises suivies sur les pages carrière"""

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
