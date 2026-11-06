"""Tests des clients HTTP et des déclarations des sources d'entreprises"""

import logging
from types import SimpleNamespace

import pytest
import requests

from job.sources.ashby import client as ashby_client
from job.sources.hackernews import source as hackernews_source
from job.sources.labonnealternance import client as labonnealternance_client
from job.sources.lever import client as lever_client
from job.sources.recruitee import client as recruitee_client
from job.sources.smartrecruiters import client as smartrecruiters_client
from job.sources.smartrecruiters import source as smartrecruiters_source
from job.sources.weworkremotely import client as weworkremotely_client
from job.sources.workable import client as workable_client
from job.sources.workday import source as workday_source
from job.sources.workingnomads import client as workingnomads_client


def record_requests(pMonkeypatch, pModule, pData, pFunction="request_json"):
    """Remplace l'appel HTTP du module et retourne la liste des appels reçus."""

    rCalls = []

    def mock_request(pMethod, pUrl, **pOptions):
        rCalls.append({"method": pMethod, "url": pUrl, **pOptions})

        return pData

    pMonkeypatch.setattr(pModule, pFunction, mock_request)

    return rCalls


@pytest.mark.parametrize(
    "pModule, pCall, pData, pExpected, pUrl, pParams",
    [
        (
            ashby_client,
            lambda: ashby_client.get_jobs("acme co"),
            {"jobs": [{"id": 1}]},
            [{"id": 1}],
            "https://api.ashbyhq.com/posting-api/job-board/acme%20co",
            {"includeCompensation": "true"},
        ),
        (
            recruitee_client,
            lambda: recruitee_client.get_offers("acme/x"),
            {"offers": [{"id": 2}]},
            [{"id": 2}],
            "https://acme%2Fx.recruitee.com/api/offers/",
            None,
        ),
        (
            lever_client,
            lambda: lever_client.get_postings("acme"),
            [{"id": 3}],
            [{"id": 3}],
            "https://api.lever.co/v0/postings/acme",
            {"mode": "json"},
        ),
        (
            workable_client,
            lambda: workable_client.get_account("acme/x"),
            {"name": "Acme", "jobs": []},
            {"name": "Acme", "jobs": []},
            "https://apply.workable.com/api/v1/widget/accounts/acme%2Fx",
            {"details": "true"},
        ),
        (
            workingnomads_client,
            workingnomads_client.get_jobs,
            [{"id": 4}],
            [{"id": 4}],
            "https://www.workingnomads.com/api/exposed_jobs/",
            None,
        ),
    ],
)
def test_client_requests_api(
    monkeypatch, pModule, pCall, pData, pExpected, pUrl, pParams
):
    """Vérifie l'adresse appelée, l'identifiant échappé et les données retournées."""

    vCalls = record_requests(monkeypatch, pModule, pData)

    assert pCall() == pExpected
    assert vCalls[0]["method"] == "GET"
    assert vCalls[0]["url"] == pUrl
    assert vCalls[0].get("pParams") == pParams


@pytest.mark.parametrize(
    "pModule, pCall, pData",
    [
        (ashby_client, lambda: ashby_client.get_jobs("acme"), {"jobs": None}),
        (recruitee_client, lambda: recruitee_client.get_offers("acme"), {}),
    ],
)
def test_client_without_jobs_returns_empty_list(monkeypatch, pModule, pCall, pData):
    """Vérifie qu'une réponse sans offres donne une liste vide."""

    record_requests(monkeypatch, pModule, pData)

    assert pCall() == []


def test_weworkremotely_reads_feed_items(monkeypatch):
    """Vérifie la lecture des éléments du flux RSS."""

    vFeed = (
        b"<rss><channel><title>WWR</title>"
        b"<item><title>Dev</title></item><item><title>Ops</title></item>"
        b"</channel></rss>"
    )
    vCalls = record_requests(
        monkeypatch, weworkremotely_client, vFeed, pFunction="request_bytes"
    )

    vItems = weworkremotely_client.get_items()

    assert [vItem.findtext("title") for vItem in vItems] == ["Dev", "Ops"]
    assert vCalls[0]["pExpectedType"] == "xml"


def test_smartrecruiters_requests_postings(monkeypatch):
    """Vérifie la pagination et le pays transmis à l'API."""

    vCalls = record_requests(monkeypatch, smartrecruiters_client, {"content": []})

    assert smartrecruiters_client.get_postings("Acme", "fr", 100) == {"content": []}
    assert vCalls[0]["url"].endswith("/companies/Acme/postings")
    assert vCalls[0]["pParams"] == {"limit": 100, "offset": 100, "country": "fr"}


def test_smartrecruiters_logs_and_raises_errors(monkeypatch, caplog):
    """Vérifie que l'erreur réseau est journalisée avec l'entreprise puis remontée."""

    def mock_request(pMethod, pUrl, **pOptions):
        raise requests.ConnectionError("refusé")

    monkeypatch.setattr(smartrecruiters_client, "request_json", mock_request)

    with caplog.at_level(logging.ERROR):
        with pytest.raises(requests.ConnectionError):
            smartrecruiters_client.get_postings("Acme", "fr")

    assert "SmartRecruiters : Acme" in caplog.text


def test_smartrecruiters_requests_posting_detail(monkeypatch):
    """Vérifie l'adresse du détail d'une offre, identifiant échappé."""

    vCalls = record_requests(monkeypatch, smartrecruiters_client, {"id": "1"})

    assert smartrecruiters_client.get_posting("Acme", "a 1") == {"id": "1"}
    assert vCalls[0]["url"].endswith("/companies/Acme/postings/a%201")


@pytest.mark.parametrize(
    "pResponse, pCode", [(SimpleNamespace(status_code=401), "401"), (None, "?")]
)
def test_labonnealternance_logs_refusal_without_key(
    monkeypatch, caplog, pResponse, pCode
):
    """Vérifie que le refus journalise le code HTTP, jamais la clé."""

    def mock_request(pMethod, pUrl, **pOptions):
        raise requests.HTTPError(response=pResponse)

    monkeypatch.setattr(labonnealternance_client, "request_json", mock_request)
    vConfig = SimpleNamespace(romes="I1304", api_key="cle-de-test")

    with caplog.at_level(logging.ERROR):
        with pytest.raises(requests.HTTPError):
            labonnealternance_client.search_jobs(vConfig)

    assert f"HTTP {pCode}" in caplog.text
    assert "cle-de-test" not in caplog.text


def make_job_config(pKnown=None):
    """Retourne une configuration de recherche minimale."""

    rConfig = SimpleNamespace(
        keyword="python",
        location="Lille",
        max_items=5,
        known_descriptions=pKnown,
    )

    return rConfig


def record_scrape_each(pMonkeypatch, pModule):
    """Remplace scrape_each pour appeler la récupération d'un seul site."""

    rCalls = []

    def mock_scrape_each(pNames, pScrape, pMaxItems, pLabel):
        rCalls.append({"names": pNames, "label": pLabel})

        return pScrape(pNames, pMaxItems)

    pMonkeypatch.setattr(pModule, "scrape_each", mock_scrape_each)

    return rCalls


def test_smartrecruiters_source_passes_country_and_known(monkeypatch):
    """Vérifie les paramètres de la source et leur transmission au service."""

    monkeypatch.setattr(
        smartrecruiters_source,
        "load_config",
        lambda: SimpleNamespace(companies="Acme", country="fr"),
    )
    vScraped = []
    monkeypatch.setattr(
        smartrecruiters_source,
        "scrape_jobs",
        lambda *pArgs: vScraped.append(pArgs) or "offres",
    )
    vCalls = record_scrape_each(monkeypatch, smartrecruiters_source)
    vJobConfig = make_job_config({"smartrecruiters": {"1": "texte"}})

    vParameters = smartrecruiters_source.load_parameters(vJobConfig)

    assert smartrecruiters_source.scrape(vParameters, vJobConfig) == "offres"
    assert vCalls == [{"names": "Acme", "label": "SmartRecruiters"}]
    assert vScraped == [("Acme", "fr", "python", "Lille", 5, {"1": "texte"})]


def test_workday_source_without_known_descriptions(monkeypatch):
    """Vérifie la source Workday quand aucune description n'est déjà connue."""

    monkeypatch.setattr(workday_source, "load_company_list", lambda pName: "site")
    vScraped = []

    def mock_scrape_jobs(pSite, pKeyword, pLocation, pMaxItems, pKnown=None):
        vScraped.append((pSite, pKeyword, pLocation, pMaxItems, pKnown))

        return "offres"

    monkeypatch.setattr(workday_source, "scrape_jobs", mock_scrape_jobs)
    record_scrape_each(monkeypatch, workday_source)
    vJobConfig = make_job_config()

    vParameters = workday_source.load_parameters(vJobConfig)

    assert workday_source.scrape(vParameters, vJobConfig) == "offres"
    assert vScraped == [("site", "python", "Lille", 5, None)]


def test_hackernews_source_passes_criteria(monkeypatch):
    """Vérifie que les critères et la limite sont transmis au service."""

    vScraped = []

    def mock_scrape_jobs(pKeyword, pLocation, pMaxItems):
        vScraped.append((pKeyword, pLocation, pMaxItems))

        return "offres"

    monkeypatch.setattr(hackernews_source, "scrape_jobs", mock_scrape_jobs)
    vJobConfig = make_job_config()

    vParameters = hackernews_source.load_parameters(vJobConfig)

    assert hackernews_source.scrape(vParameters, vJobConfig) == "offres"
    assert vScraped == [("python", "Lille", 5)]
