"""Tests de la source La bonne alternance"""

from types import SimpleNamespace

from job.sources.labonnealternance import client, source
from job.sources.labonnealternance.parser import parse_job

JOB = {
    "identifier": {"id": "68a1", "partner_label": "France Travail"},
    "workplace": {"name": "Atelier Mécanique", "brand": None},
    "location": {"address": "12 rue de l'Usine 59000 Lille"},
    "contract": {"type": ["Apprentissage", "Professionnalisation"], "duration": 24},
    "offer": {
        "title": "Technicien de maintenance en alternance",
        "description": "<p>Maintenance préventive</p>",
        "desired_skills": ["Électricité", "Mécanique"],
        "target_diploma": None,
    },
    "publication": {"creation": "2026-10-20T08:00:00.000Z"},
    "apply": {"url": "https://labonnealternance.apprentissage.beta.gouv.fr/x"},
}


def test_location_is_read_in_the_workplace():
    """Vérifie le lieu lu dans l'établissement quand location est vide."""

    vJob = parse_job(
        {
            **JOB,
            "location": None,
            "workplace": {
                "name": "Azur Linge Service",
                "location": {"address": "120 AVENUE JEAN MAUBERT 06130 GRASSE"},
            },
        }
    )

    assert vJob["location"] == "120 AVENUE JEAN MAUBERT 06130 GRASSE"


def test_parse_job_reads_each_block():
    """Vérifie la lecture des blocs de l'offre."""

    vJob = parse_job(JOB)

    assert vJob["company"] == "Atelier Mécanique"
    assert vJob["contract_type"] == "Apprentissage, Professionnalisation"
    assert vJob["employment_type"] == "24 mois"
    assert vJob["requirements"] == "Électricité, Mécanique"
    assert vJob["description"] == "Maintenance préventive"
    assert vJob["job_type"] == "France Travail"


def test_scrape_sends_key_and_trades_then_filters(monkeypatch):
    """Vérifie la clé en en-tête, les métiers par défaut et le filtre du lieu."""

    monkeypatch.setenv("LBA_API_KEY", "cle")
    monkeypatch.delenv("LBA_ROMES", raising=False)
    vCalls = []

    def fake_request(_pMethod, _pUrl, **pOptions):
        vCalls.append(pOptions)
        vElsewhere = {
            **JOB,
            "identifier": {"id": "2"},
            "location": {"address": "Brest"},
        }
        return {"jobs": [JOB, vElsewhere]}

    monkeypatch.setattr(client, "request_json", fake_request)
    vConfig = SimpleNamespace(keyword=None, location="Lille", max_items=None)

    vJobs = source.SOURCE.scrape(source.load_parameters(vConfig), vConfig)

    assert list(vJobs["source_id"]) == ["68a1"]
    assert vCalls[0]["pHeaders"] == {"Authorization": "Bearer cle"}
    assert vCalls[0]["pParams"]["romes"].startswith("I1304")
