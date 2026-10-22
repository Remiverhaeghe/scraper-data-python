"""Tests des flux de télétravail (Remote OK, Working Nomads, We Work Remotely)"""

from types import SimpleNamespace

from defusedxml import ElementTree

from job.sources.remoteok import client as remoteok_client
from job.sources.remoteok.parser import parse_job as parse_remoteok
from job.sources.remoteok.parser import repair_text
from job.sources.weworkremotely.parser import parse_items
from job.sources.workingnomads.parser import parse_job as parse_nomads
from job.sources.workingnomads.source import SOURCE as WORKING_NOMADS

RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
  <item>
    <title>Apollo GraphQL: Senior Solution Engineer</title>
    <region>Anywhere in the World</region>
    <category>Sales and Marketing</category>
    <type>Full-Time</type>
    <description>&lt;p&gt;Ship fast&lt;/p&gt;</description>
    <pubDate>Wed, 21 Oct 2026 20:58:30 +0000</pubDate>
    <guid>https://weworkremotely.com/remote-jobs/apollo-senior</guid>
    <link>https://weworkremotely.com/remote-jobs/apollo-senior</link>
  </item>
</channel></rss>"""


def test_remoteok_skips_legal_notice_and_repairs_text(monkeypatch):
    """Vérifie le retrait des conditions d'usage et la réparation des accents."""

    monkeypatch.setattr(
        remoteok_client,
        "request_json",
        lambda *_pArgs, **_pOptions: [
            {"legal": "API Terms of Service"},
            {"id": "1137548", "position": "Risk Analyst"},
        ],
    )

    assert remoteok_client.get_jobs() == [{"id": "1137548", "position": "Risk Analyst"}]
    assert repair_text("Analyst â\x80\x93 Remote") == "Analyst – Remote"
    assert repair_text("Déjà correct") == "Déjà correct"

    vJob = parse_remoteok(
        {"id": 1, "position": "Dev", "salary_min": 0, "tags": ["python", "sql"]}
    )

    assert vJob["salary_currency"] is None
    assert vJob["skills"] == "python, sql"
    assert vJob["remote"]


def test_working_nomads_reads_id_from_url_and_filters(monkeypatch):
    """Vérifie l'identifiant lu dans l'adresse et le filtre par mot-clé du flux."""

    vJob = parse_nomads(
        {
            "url": "https://www.workingnomads.com/job/go/1960693/",
            "title": "Senior Angular Developer",
            "tags": "angular,typescript",
        }
    )

    assert vJob["source_id"] == "1960693"
    assert vJob["skills"] == "angular, typescript"

    monkeypatch.setattr(
        "job.sources.workingnomads.source.get_jobs",
        lambda: [
            {"url": "https://x/job/go/1/", "title": "Angular Developer"},
            {"url": "https://x/job/go/2/", "title": "Designer"},
        ],
    )
    vConfig = SimpleNamespace(keyword="angular", location=None, max_items=None)

    vJobs = WORKING_NOMADS.scrape(WORKING_NOMADS.load_parameters(vConfig), vConfig)

    assert list(vJobs["source_id"]) == ["1"]


def test_we_work_remotely_items():
    """Vérifie la lecture du flux RSS : entreprise et poste séparés du titre."""

    vJobs = parse_items(ElementTree.fromstring(RSS).findall("./channel/item"))
    vJob = vJobs.iloc[0]

    assert vJob["company"] == "Apollo GraphQL"
    assert vJob["title"] == "Senior Solution Engineer"
    assert vJob["description"] == "Ship fast"
    assert vJob["published_at"].startswith("2026-10-21T20:58:30")
